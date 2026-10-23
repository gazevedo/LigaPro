import asyncio
import importlib
import os
from threading import Event
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from fastapi.testclient import TestClient

from app.api.dependencies import get_auth_service, get_current_user
from app.config.settings import get_settings


def module():
    get_settings.cache_clear()
    with patch.dict(
        os.environ,
        {
            "MONGODB_CONNECTION_STRING": "mongodb://localhost",
            "MONGODB_DATABASE_NAME": "test",
            "JWT_SECRET_KEY": "test-only-key-with-at-least-32-characters",
        },
    ):
        result = importlib.import_module("app.main")
    get_settings.cache_clear()
    return result


def test_broken_live_room_does_not_stop_offline_matches_or_notifications():
    main = module()
    manager = Mock(start_due=AsyncMock(side_effect=RuntimeError("broken room")))
    repo, config = Mock(), Mock()
    with (
        patch.object(main, "process_due") as games,
        patch.object(main, "send_match_reminders") as reminders,
    ):
        asyncio.run(main.run_game_maintenance(manager, repo, config))
    games.assert_called_once_with(repo)
    reminders.assert_called_once_with(repo, config)


def test_offline_processing_failure_does_not_stop_other_stages():
    main = module()
    manager = Mock(start_due=AsyncMock())
    repo, config = Mock(), Mock()
    with (
        patch.object(main, "process_due", side_effect=RuntimeError("game failed")),
        patch.object(main, "send_match_reminders") as reminders,
    ):
        asyncio.run(main.run_game_maintenance(manager, repo, config))
    manager.start_due.assert_awaited_once()
    reminders.assert_called_once_with(repo, config)


def application(main):
    with patch.dict(
        os.environ,
        {
            "MONGODB_CONNECTION_STRING": "mongodb://localhost",
            "MONGODB_DATABASE_NAME": "test",
            "JWT_SECRET_KEY": "test-only-key-with-at-least-32-characters",
        },
    ):
        app = main.create_app()
    get_settings.cache_clear()
    return app


def test_competition_reads_return_saved_data_without_simulating_matches():
    main = module()
    app = application(main)
    user, repo = Mock(), Mock()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[main.game.repository] = lambda: repo
    app.state.request_game_tick = AsyncMock()
    events = []

    def process(**kwargs):
        assert kwargs == {"max_matches": 10}
        events.append("processed")

    def read(_user, _division_id=None):
        events.append("read")
        return {"games": 4}

    with patch.object(main.game, "CompetitionService") as competition:
        competition.return_value.process_due.side_effect = process
        competition.return_value.table.side_effect = read
        competition.return_value.matches.side_effect = read
        client = TestClient(app)
        for path in ("/api/competition", "/api/competition/matches"):
            response = client.get(path)
            assert response.status_code == 200
            assert response.json() == {"games": 4}
    assert events == ["read", "read"]
    competition.return_value.process_due.assert_not_called()
    app.state.request_game_tick.assert_not_awaited()


def test_unauthenticated_reads_do_not_process_matches():
    main = module()
    app = application(main)
    app.dependency_overrides[get_auth_service] = lambda: Mock()
    with patch.object(main.game, "CompetitionService") as competition:
        for path in ("/api/competition", "/api/competition/matches"):
            assert TestClient(app).get(path).status_code == 401
    competition.assert_not_called()


def test_screen_reads_do_not_trigger_scheduled_maintenance():
    main = module()
    app = application(main)
    app.state.request_game_tick = AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: Mock()
    app.dependency_overrides[main.game.repository] = lambda: Mock()
    with patch.object(main.game, "ClubService") as club:
        club.return_value.status.return_value = {"club": None}
        assert TestClient(app).get("/api/game/status").status_code == 200
    app.state.request_game_tick.assert_not_awaited()


def test_api_timer_runs_maintenance_without_screen_requests():
    main = module()
    app = application(main)
    manager = Mock(recover=AsyncMock(), close=AsyncMock())
    config = SimpleNamespace(mongodb_database_name="test")
    ran = Event()

    async def maintenance(*args, **kwargs):
        ran.set()

    with (
        patch.object(main, "get_settings", return_value=config),
        patch.object(main, "create_client", return_value=MagicMock()),
        patch("mock_database.import_database"),
        patch.object(main, "GameRepository", return_value=Mock()),
        patch("app.services.live_match.MatchRoomManager", return_value=manager),
        patch.object(main, "process_due"),
        patch("app.services.game_scheduler.next_game_delay", return_value=30),
        patch.object(main, "run_game_maintenance", side_effect=maintenance) as task,
    ):
        with TestClient(app):
            assert ran.wait(2)
            task.assert_awaited_once()
    manager.close.assert_awaited_once()


def test_serverless_request_does_not_wait_indefinitely_for_another_initialization():
    main = module()
    app = application(main)
    app.state.database_lock = Mock()
    app.state.database_lock.acquire.return_value = False
    response = TestClient(app).get("/api/health")
    assert response.status_code == 503
    assert "inicializando" in response.json()["detail"]


def test_serverless_maintenance_waits_until_initial_league_is_ready():
    main = module()
    repository = Mock()
    repository.find.return_value = None
    manager = Mock(start_due=AsyncMock())
    with patch.object(main, "is_serverless_runtime", return_value=True):
        asyncio.run(main.run_game_maintenance(manager, repository, Mock()))
    repository.find.assert_called_once_with(
        "game_state", {"_id": "initial_universe", "status": "ready"}
    )
    manager.start_due.assert_not_awaited()


def test_external_worker_mode_does_not_run_offline_simulation_from_api():
    main = module()
    manager = Mock(start_due=AsyncMock())
    with (
        patch.dict(os.environ, {"GAME_SCHEDULER_MODE": "external"}),
        patch.object(main, "process_due") as games,
        patch.object(main, "send_match_reminders"),
    ):
        asyncio.run(main.run_game_maintenance(manager, Mock(), Mock()))
    games.assert_not_called()
    manager.start_due.assert_awaited_once()


def test_startup_scheduler_runs_even_when_live_maintenance_is_blocked():
    main = module()

    async def scenario():
        app = application(main)
        manager = Mock(recover=AsyncMock(), close=AsyncMock())
        config = SimpleNamespace(mongodb_database_name="test")
        client = MagicMock()
        ran = Event()
        maintenance_started = asyncio.Event()
        release = Event()

        async def maintenance(*args, **kwargs):
            assert kwargs == {"scheduled": False}
            maintenance_started.set()
            await asyncio.Event().wait()

        def process(repository):
            ran.set()
            assert release.wait(2)
            # MongoDB must stay open until the running simulation finishes.
            client.close.assert_not_called()

        with (
            patch.dict(os.environ, {"GAME_SCHEDULER_MODE": "embedded"}),
            patch.object(main, "get_settings", return_value=config),
            patch.object(main, "create_client", return_value=client),
            patch.object(main, "initialize_database"),
            patch.object(main, "GameRepository", return_value=Mock()),
            patch("app.services.live_match.MatchRoomManager", return_value=manager),
            patch.object(main, "run_game_maintenance", side_effect=maintenance),
            patch.object(main, "process_due", side_effect=process) as games,
        ):
            async with main.lifespan(app):
                await asyncio.wait_for(maintenance_started.wait(), 2)
                assert await asyncio.to_thread(ran.wait, 2)
                release.set()
            games.assert_called_once()
            client.close.assert_called_once()
            manager.close.assert_awaited_once()

    asyncio.run(scenario())


def test_external_mode_does_not_start_an_embedded_scheduler():
    main = module()

    async def scenario():
        app = application(main)
        manager = Mock(recover=AsyncMock(), close=AsyncMock())
        with (
            patch.dict(os.environ, {"GAME_SCHEDULER_MODE": "external"}),
            patch.object(
                main, "get_settings", return_value=SimpleNamespace(mongodb_database_name="test")
            ),
            patch.object(main, "create_client", return_value=MagicMock()),
            patch.object(main, "initialize_database"),
            patch.object(main, "GameRepository", return_value=Mock()),
            patch("app.services.live_match.MatchRoomManager", return_value=manager),
            patch.object(main, "run_game_scheduler", new_callable=AsyncMock) as scheduler,
        ):
            async with main.lifespan(app):
                pass
            scheduler.assert_not_awaited()

    asyncio.run(scenario())


def test_serverless_live_progress_does_not_depend_on_background_rooms():
    main = module()
    manager = Mock(start_due=AsyncMock())
    repository = Mock()
    repository.find.return_value = {"status": "ready"}
    with (
        patch.object(main, "is_serverless_runtime", return_value=True),
        patch.object(main, "process_due"),
        patch.object(main, "send_match_reminders"),
    ):
        asyncio.run(main.run_game_maintenance(manager, repository, Mock()))
    manager.start_due.assert_not_awaited()
