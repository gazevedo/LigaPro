from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app, create_app
from app.models.game import utcnow
from app.repositories.game import GameRepository
from app.schemas.game import ClubInput
from app.services.competition import CompetitionService, SeasonFinalizationService
from app.services.game import ClubService
from app.services.monthly_finance import MonthlyFinanceService
from app.services.player_development import PlayerAgingService


def counts(database):
    return {
        name: database[name].count_documents({})
        for name in (
            "clubs",
            "players",
            "player_contracts",
            "divisions",
            "seasons",
            "season_clubs",
            "standings",
            "matches",
            "youth_players",
            "calendar_events",
        )
    }


def test_startup_base_is_complete_without_a_user_or_club_registration(client):
    repo = GameRepository(app.state.database)
    assert CompetitionService(repo).initialize_universe() is True
    database = app.state.database
    assert database.users.count_documents({}) == 0
    assert database.clubs.count_documents({"is_bot": True}) == 20
    assert database.players.count_documents({}) == 500
    assert database.player_contracts.count_documents({}) == 500
    assert database.matches.count_documents({}) == 380
    assert database.youth_players.count_documents({}) == 60
    before = counts(database)
    marker = database.game_state.find_one({"_id": "initial_universe"})
    assert CompetitionService(GameRepository(database)).initialize_universe() is False
    assert counts(database) == before
    assert database.game_state.find_one({"_id": "initial_universe"}) == marker


def test_simultaneous_startups_create_only_one_base(client):
    database = app.state.database

    def prepare(_):
        return CompetitionService(GameRepository(database)).initialize_universe()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(prepare, range(2)))
    assert sorted(results) == [False, True]
    assert database.clubs.count_documents({}) == 20
    assert database.matches.count_documents({}) == 380
    assert database.game_state.count_documents({"_id": "initial_universe"}) == 1


def test_club_registration_reuses_prepared_base(client):
    database = app.state.database
    CompetitionService(GameRepository(database)).initialize_universe()
    before = counts(database)
    registration = client.post(
        "/api/auth/register",
        json={"name": "Manager", "email": "manager@example.com", "password": "password123"},
    )
    assert registration.status_code == 201
    headers = {"Authorization": "Bearer " + registration.json()["access_token"]}
    response = client.post(
        "/api/clubs",
        headers=headers,
        json={
            "name": "123",
            "country_id": "BR",
            "badge_id": "blue",
            "stadium_name": "123",
        },
    )
    assert response.status_code == 201, response.text
    assert database.divisions.count_documents({}) == before["divisions"]
    assert database.matches.count_documents({}) == before["matches"]
    assert database.clubs.count_documents({"is_bot": True, "active": {"$ne": False}}) == 19
    database.game_state.delete_one({"_id": "initial_universe"})
    before = counts(database)
    assert CompetitionService(GameRepository(database)).initialize_universe() is True
    assert counts(database) == before


def test_failed_preparation_rolls_back_and_next_start_can_retry(client):
    database = app.state.database
    original = CompetitionService.create_bot

    def fail_after_creating_bot(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("interrupted preparation")

    with patch.object(CompetitionService, "create_bot", side_effect=fail_after_creating_bot):
        with pytest.raises(RuntimeError):
            CompetitionService(GameRepository(database)).initialize_universe()
    assert database.clubs.count_documents({}) == 0
    assert database.players.count_documents({}) == 0
    assert database.game_state.find_one({"_id": "initial_universe"}) is None
    assert CompetitionService(GameRepository(database)).initialize_universe() is True
    assert database.clubs.count_documents({}) == 20


def test_backend_startup_prepares_base_once_before_serving_requests(client):
    with TestClient(create_app()) as started:
        database = started.app.state.database
        assert database.game_state.find_one({"_id": "initial_universe"})
        assert database.clubs.count_documents({}) == 20
        before = counts(database)
    with TestClient(create_app()) as restarted:
        assert counts(restarted.app.state.database) == before


def test_first_health_request_without_lifespan_prepares_base(client):
    cold = create_app()
    try:
        response = TestClient(cold).get("/api/health")
        assert response.status_code == 200
        database = cold.state.database
        assert database.users.count_documents({}) == 0
        assert database.clubs.count_documents({"active": True, "is_bot": True}) == 20
        assert CompetitionService.initial_universe_ready(GameRepository(database))
        before = counts(database)
        assert TestClient(cold).get("/api/health").status_code == 200
        assert counts(database) == before
    finally:
        cold.state.database_client.close()


def test_stale_marker_does_not_hide_deleted_clubs(client):
    database = app.state.database
    service = CompetitionService(GameRepository(database))
    service.initialize_universe()
    slots = set(row["_id"] for row in database.season_clubs.find({}))
    database.clubs.delete_many({})
    assert service.initialize_universe() is True
    assert CompetitionService.initial_universe_ready(GameRepository(database))
    assert database.clubs.count_documents({"active": True, "is_bot": True}) == 20
    assert set(row["_id"] for row in database.season_clubs.find({})) == slots
    assert service.initialize_universe() is False


def test_existing_empty_division_is_completed_without_duplication(client):
    database = app.state.database
    repo = GameRepository(database)
    season = CompetitionService.create_season(repo, utcnow())
    division = CompetitionService.division_for_tier(repo, 0)
    database.game_state.insert_one({"_id": "initial_universe", "season_id": season["_id"]})
    assert CompetitionService(repo).initialize_universe() is True
    assert database.divisions.count_documents({}) == 1
    assert database.divisions.find_one({})["_id"] == division["_id"]
    assert CompetitionService.initial_universe_ready(GameRepository(database))


def test_missing_standings_and_games_are_repaired_preserving_clubs(client):
    database = app.state.database
    service = CompetitionService(GameRepository(database))
    service.initialize_universe()
    clubs = set(row["_id"] for row in database.clubs.find({}))
    database.standings.delete_one({})
    database.matches.delete_one({})
    assert service.initialize_universe() is True
    assert set(row["_id"] for row in database.clubs.find({})) == clubs
    assert CompetitionService.initial_universe_ready(GameRepository(database))


@pytest.mark.parametrize("managed", [False, True])
def test_next_season_keeps_full_leagues_and_handles_relegation(client, managed):
    database = app.state.database
    repo = GameRepository(database)
    service = CompetitionService(repo)
    service.initialize_universe()
    human = None
    if managed:
        human = ClubService(repo).create(
            SimpleNamespace(id=str(ObjectId())),
            ClubInput(name="Rebaixado", country_id="BR", badge_id="blue"),
        )
        database.standings.update_many({}, {"$set": {"points": 100}})
        database.standings.update_one({"club_id": ObjectId(human["id"])}, {"$set": {"points": 0}})
    season = service.current(repo)
    database.matches.update_many({}, {"$set": {"status": "completed"}})
    with (
        patch.object(CompetitionService, "play_due"),
        patch.object(MonthlyFinanceService, "process_due"),
        patch.object(PlayerAgingService, "process"),
    ):
        SeasonFinalizationService(repo).finalize(season["_id"], season["ends_at"])
    upcoming = service.current(repo)
    assert upcoming and upcoming["_id"] != season["_id"]
    assert service.initial_universe_ready(repo)
    divisions = list(database.divisions.find({"active": True}))
    assert len(divisions) == (2 if managed else 1)
    for division in divisions:
        query = {"season_id": upcoming["_id"], "division_id": division["_id"]}
        assert database.season_clubs.count_documents(query) == 20
        assert database.matches.count_documents(query) == 380
    if managed:
        assert database.clubs.find_one({"_id": ObjectId(human["id"])})["division_tier"] == 1
    before = counts(database)
    with patch.object(CompetitionService, "play_due"):
        SeasonFinalizationService(repo).finalize(season["_id"], season["ends_at"])
    assert counts(database) == before


def test_two_filled_series_leave_next_series_with_twenty_bots(client):
    database = app.state.database
    repo = GameRepository(database)
    CompetitionService(repo).initialize_universe()
    for index in range(40):
        ClubService(repo).create(
            SimpleNamespace(id=str(ObjectId())),
            ClubInput(
                name=f"Manager {index}",
                country_id="BR",
                badge_id="blue",
            ),
        )
    season = CompetitionService.current(repo)
    assert database.divisions.count_documents({"active": True}) == 3
    for tier in range(3):
        division = database.divisions.find_one({"tier": tier})
        query = {"season_id": season["_id"], "division_id": division["_id"]}
        assert database.season_clubs.count_documents(query) == 20
        assert database.season_clubs.count_documents({**query, "is_bot": True}) == (
            20 if tier == 2 else 0
        )
        assert database.matches.count_documents(query) == 380
    before = counts(database)
    assert CompetitionService(repo).initialize_universe() is False
    assert counts(database) == before


def test_failed_serverless_initialization_can_retry_on_next_request(client):
    from app.main import initialize_database

    cold = create_app()
    attempts = 0

    def initialize(database):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("interrupted initialization")
        initialize_database(database)

    try:
        with patch("app.main.initialize_database", side_effect=initialize):
            assert (
                TestClient(cold, raise_server_exceptions=False).get("/api/health").status_code
                == 500
            )
            assert not getattr(cold.state, "database_ready", False)
            assert TestClient(cold).get("/api/health").status_code == 200
        assert attempts == 2
        assert cold.state.database.clubs.count_documents({"active": True, "is_bot": True}) == 20
    finally:
        if getattr(cold.state, "database_ready", False):
            cold.state.database_client.close()


def test_health_repairs_empty_base_even_when_connection_was_already_initialized(client):
    # The fixture keeps the warm application's connection but removes all game data.
    assert app.state.database_ready is True
    assert app.state.database.clubs.count_documents({}) == 0
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["league"] == {
        "status": "ready",
        "divisions": 1,
        "clubs": 20,
        "bots": 20,
        "matches": 380,
    }
    before = counts(app.state.database)
    assert client.get("/api/health").json()["league"]["clubs"] == 20
    assert counts(app.state.database) == before


def test_health_retries_repair_with_old_marker_but_no_clubs(client):
    database = app.state.database
    CompetitionService(GameRepository(database)).initialize_universe()
    database.clubs.delete_many({})
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["league"]["clubs"] == 20
    assert database.clubs.count_documents({"active": True, "is_bot": True}) == 20


def test_health_does_not_report_ready_when_preparation_fails(client):
    with patch.object(
        CompetitionService, "initialize_universe", side_effect=RuntimeError("preparation failed")
    ):
        response = TestClient(app, raise_server_exceptions=False).get("/api/health")
    assert response.status_code == 500
    assert response.json().get("status") != "ok"
