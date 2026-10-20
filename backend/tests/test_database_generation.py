from datetime import timedelta
from unittest.mock import patch

import pytest
from bson import ObjectId
from pymongo.errors import OperationFailure
from pymongo.synchronous.collection import Collection

from app.main import app
from app.models.game import round_match_time, utcnow
from app.repositories.game import GameRepository
from mock_database import SEED_MARKER, import_database


def test_offline_import_builds_complete_league_on_current_date_and_is_idempotent(client):
    database = app.state.database
    now = utcnow().replace(microsecond=0)
    with patch("mock_database.utcnow", return_value=now):
        assert import_database(database) is True
    assert database.clubs.count_documents({"is_bot": True}) == 20
    assert database.players.count_documents({}) == 500
    assert database.player_contracts.count_documents({}) == 500
    assert database.youth_players.count_documents({}) == 60
    assert database.matches.count_documents({}) == 380
    assert database.season_clubs.count_documents({}) == 20
    assert database.standings.count_documents({}) == 20
    assert (
        database.matches.count_documents(
            {"round": 1, "date": round_match_time(now + timedelta(minutes=15))}
        )
        == 10
    )
    player = database.players.find_one({})
    database.players.update_one({"_id": player["_id"]}, {"$set": {"strength": 99}})
    counts = {name: database[name].count_documents({}) for name in database.list_collection_names()}
    assert import_database(database) is False
    assert database.players.find_one({"_id": player["_id"]})["strength"] == 99
    assert counts == {
        name: database[name].count_documents({}) for name in database.list_collection_names()
    }
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["initialization"]["percentage"] == 100
    assert response.json()["league"]["bots"] == 20


def test_import_resumes_after_failure_without_recreating_or_redating_documents(client):
    database = app.state.database
    original = Collection.bulk_write

    def fail(collection, *args, **kwargs):
        if collection.name == "players":
            raise OperationFailure("interrupted import")
        return original(collection, *args, **kwargs)

    now = utcnow().replace(microsecond=0)
    with (
        patch("mock_database.utcnow", return_value=now),
        patch.object(Collection, "bulk_write", fail),
    ):
        with pytest.raises(OperationFailure):
            import_database(database)
    assert database.game_state.find_one({"_id": "initial_universe"})["status"] == "preparing"
    assert database.game_state.find_one({"_id": SEED_MARKER})["status"] == "importing"
    assert database.clubs.count_documents({}) == 20
    with patch("mock_database.utcnow", return_value=now + timedelta(days=1)):
        assert import_database(database) is True
    assert database.clubs.count_documents({}) == 20
    assert database.players.count_documents({}) == 500
    assert database.seasons.find_one({"status": "active"})["starts_at"] == now
    assert (
        database.matches.count_documents(
            {"round": 1, "date": round_match_time(now + timedelta(minutes=15))}
        )
        == 10
    )


def test_import_refuses_to_overwrite_an_existing_unprepared_league(client):
    database = app.state.database
    database.clubs.insert_one({"_id": ObjectId(), "name": "Existente"})
    with pytest.raises(RuntimeError, match="não sobrescreve"):
        import_database(database)
    assert database.clubs.count_documents({}) == 1


def test_health_only_reports_progress_and_never_generates_data(client):
    database = app.state.database
    before = {name: database[name].count_documents({}) for name in database.list_collection_names()}
    with patch.object(GameRepository, "initialize", side_effect=AssertionError("generation")):
        for _ in range(2):
            response = client.get("/api/health")
            assert response.status_code == 202
            assert response.json()["initialization"]["status"] == "waiting_for_import"
            assert "mock_database.py" in response.json()["detail"]
    assert before == {
        name: database[name].count_documents({}) for name in database.list_collection_names()
    }


def test_imported_base_supports_registration_replacing_one_bot(client):
    from test_game import account, create

    database = app.state.database
    import_database(database)
    headers = account(client, 987)
    club = create(client, headers)
    assert database.season_clubs.count_documents({}) == 20
    assert database.standings.count_documents({"is_bot": True}) == 19
    assert database.matches.count_documents({}) == 380
    assert database.season_clubs.find_one({"club_id": ObjectId(club["id"])})
    assert database.players.count_documents({"current_club_id": ObjectId(club["id"])}) == 25


def test_parallel_cold_instances_import_only_one_universe(client):
    from concurrent.futures import ThreadPoolExecutor

    database = app.state.database
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: import_database(database), range(2)))
    assert database.clubs.count_documents({}) == 20
    assert database.players.count_documents({}) == 500
    assert database.matches.count_documents({}) == 380
    assert database.game_state.find_one({"_id": SEED_MARKER})["status"] == "ready"


def test_new_club_table_and_fixtures_are_available_without_processing_games(client):
    from test_game import account, create

    from app.services.competition import CompetitionService

    database = app.state.database
    import_database(database)
    headers = account(client, 988)
    club = create(client, headers)
    with patch.object(
        CompetitionService, "process_due", side_effect=AssertionError("screen simulation")
    ):
        table = client.get("/api/competition", headers=headers)
        games = client.get("/api/competition/matches", headers=headers)
    assert table.status_code == 200, table.text
    assert games.status_code == 200, games.text
    assert len(table.json()["standings"]) == 20
    assert any(row["club_id"] == club["id"] for row in table.json()["standings"])
    assert len(games.json()) == 38
    assert all(club["id"] in (row["home_club_id"], row["away_club_id"]) for row in games.json())
