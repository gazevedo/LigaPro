from concurrent.futures import ThreadPoolExecutor
from time import monotonic, sleep
from unittest.mock import patch

from fastapi.testclient import TestClient
from pymongo.errors import OperationFailure
from pymongo.synchronous.collection import Collection

from app.main import app, create_app
from app.repositories.game import GameRepository


def test_schema_resumes_from_last_confirmed_collection(client, monkeypatch):
    database = app.state.database
    database.game_state.delete_one({"_id": GameRepository.SCHEMA_MARKER})
    calls = []
    original = Collection.create_indexes

    def create(collection, models, **kwargs):
        calls.append(collection.name)
        return original(collection, models, **kwargs)

    monkeypatch.setattr(Collection, "create_indexes", create)
    assert GameRepository(database).initialize(max_steps=1) is False
    assert len(calls) == 1
    first = calls[0]
    assert GameRepository(database).initialize(max_steps=1) is False
    assert len(calls) == 2
    assert calls.count(first) == 1
    assert GameRepository(database).initialize() is True
    assert calls.count(first) == 1


def test_health_reports_every_generation_stage_and_reaches_one_hundred(client):
    database = app.state.database
    database.game_state.delete_one({"_id": GameRepository.SCHEMA_MARKER})
    percentages, stages = [], set()
    for _ in range(120):
        with patch("app.services.health.monotonic", side_effect=[0, 0, 5]):
            response = client.get("/api/health")
        assert response.status_code in (200, 202), response.text
        data = response.json()
        progress = data["initialization"]
        percentages.append(progress["percentage"])
        stages.add(progress["stage"])
        assert progress["completed_steps"] == sum(step["completed"] for step in progress["steps"])
        assert progress["total_steps"] == sum(step["total"] for step in progress["steps"])
        if response.status_code == 200:
            break
        assert progress["percentage"] < 100
        assert response.headers["Retry-After"] == "1"
    else:
        raise AssertionError("Generation did not finish")
    assert percentages == sorted(percentages)
    assert percentages[-1] == 100
    assert stages == {"indexes", "catalogs", "clubs", "calendar", "ready"}
    assert data["league"] == {
        "status": "ready",
        "divisions": 1,
        "clubs": 20,
        "bots": 20,
        "matches": 380,
    }
    before = database.game_state.find_one({"_id": "initial_universe"})
    assert client.get("/api/health").json()["initialization"]["percentage"] == 100
    assert database.game_state.find_one({"_id": "initial_universe"}) == before


def test_health_with_reported_network_latency_advances_instead_of_restarting(client, monkeypatch):
    database = app.state.database
    database.game_state.delete_one({"_id": GameRepository.SCHEMA_MARKER})
    create, update, find = Collection.create_indexes, Collection.update_one, Collection.find_one

    def slow_create(collection, *args, **kwargs):
        sleep(0.113)
        return create(collection, *args, **kwargs)

    def slow_update(collection, query, *args, **kwargs):
        if collection.name == "game_state" and query.get("_id") == GameRepository.SCHEMA_MARKER:
            sleep(0.113)
        return update(collection, query, *args, **kwargs)

    def slow_find(collection, query=None, *args, **kwargs):
        if (
            collection.name == "game_state"
            and query
            and query.get("_id") == GameRepository.SCHEMA_MARKER
        ):
            sleep(0.113)
        return find(collection, query, *args, **kwargs)

    monkeypatch.setattr(Collection, "create_indexes", slow_create)
    monkeypatch.setattr(Collection, "update_one", slow_update)
    monkeypatch.setattr(Collection, "find_one", slow_find)
    percentages, durations = [], []
    for _ in range(12):
        started = monotonic()
        response = client.get("/api/health")
        durations.append(monotonic() - started)
        assert response.status_code in (200, 202), response.text
        percentages.append(response.json()["initialization"]["percentage"])
        if response.status_code == 200:
            break
    assert len(percentages) > 1
    assert percentages == sorted(percentages)
    assert percentages[-1] == 100
    assert sum(durations) > 8  # The former single startup budget could not fit this work.
    assert max(durations) < 8
    assert database.clubs.count_documents({"active": True, "is_bot": True}) == 20


def test_vercel_startup_does_not_create_indexes_before_serving_health(client, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    with patch.object(GameRepository, "initialize", side_effect=AssertionError("heavy startup")):
        with TestClient(create_app()) as cold:
            assert cold.app.state.database_schema_ready is False
            assert cold.get("/docs").status_code == 200


def test_simultaneous_schema_generations_keep_one_checkpoint_per_step(client):
    database = app.state.database
    database.game_state.delete_one({"_id": GameRepository.SCHEMA_MARKER})
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: GameRepository(database).initialize(), range(2)))
    assert results == [True, True]
    state = database.game_state.find_one({"_id": GameRepository.SCHEMA_MARKER})
    assert len(state["completed"]) == len(set(state["completed"]))
    assert all(step["completed"] for step in GameRepository(database).schema_progress())
    assert database.countries.count_documents({}) == 249
    assert database.club_badges.count_documents({}) == 8


def test_failed_schema_step_reports_progress_without_exposing_database_details(client):
    database = app.state.database
    database.game_state.delete_one({"_id": GameRepository.SCHEMA_MARKER})
    with patch.object(
        Collection, "create_indexes", side_effect=OperationFailure("private database detail")
    ):
        response = client.get("/api/health")
    assert response.status_code == 503
    progress = response.json()["initialization"]
    assert progress["status"] == "failed"
    assert progress["percentage"] == 0
    assert progress["stage"] == "indexes"
    assert progress["error"] == "OperationFailure"
    assert "private database detail" not in response.text
    assert client.get("/api/health").json()["initialization"]["percentage"] == 100
