from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app, create_app
from app.repositories.game import GameRepository
from app.services.competition import CompetitionService


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
