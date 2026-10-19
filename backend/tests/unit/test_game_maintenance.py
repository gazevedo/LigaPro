import asyncio
import importlib
import os
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


def test_authenticated_competition_reads_finish_batch_before_reading_results():
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

    def read(_user):
        assert events[-1] == "processed"
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
    assert events == ["processed", "read", "processed", "read"]
    app.state.request_game_tick.assert_not_awaited()


def test_unauthenticated_reads_do_not_process_matches():
    main = module()
    app = application(main)
    app.dependency_overrides[get_auth_service] = lambda: Mock()
    with patch.object(main.game, "CompetitionService") as competition:
        for path in ("/api/competition", "/api/competition/matches"):
            assert TestClient(app).get(path).status_code == 401
    competition.assert_not_called()


def test_async_maintenance_runs_after_response_body_and_finishes_before_request_ends():
    main = module()
    app = application(main)
    events = []

    class ObserveResponse:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            async def observed_send(message):
                if message["type"] == "http.response.body" and not message.get("more_body"):
                    events.append("body")
                await send(message)

            await self.app(scope, receive, observed_send)

    async def maintenance():
        assert events == ["body"]
        await asyncio.sleep(0)
        events.append("maintenance_finished")

    app.add_middleware(ObserveResponse)
    app.state.request_game_tick = maintenance
    app.dependency_overrides[get_auth_service] = lambda: Mock()
    TestClient(app).get("/api/game/status")
    assert events == ["body", "maintenance_finished"]


def test_timer_and_requests_share_maintenance_and_throttle_following_reads():
    main = module()
    app = application(main)
    app.dependency_overrides[get_auth_service] = lambda: Mock()
    manager = Mock(recover=AsyncMock(), close=AsyncMock())
    config = SimpleNamespace(mongodb_database_name="test")
    with (
        patch.object(main, "get_settings", return_value=config),
        patch.object(main, "create_client", return_value=MagicMock()),
        patch.object(main, "GameRepository", return_value=Mock()),
        patch.object(main.CompetitionService, "bootstrap"),
        patch.object(main.CompetitionService, "initialize_universe"),
        patch.object(main.ContractService, "bootstrap"),
        patch.object(main, "bootstrap_player_attributes"),
        patch.object(main, "bootstrap_economy"),
        patch("app.services.live_match.MatchRoomManager", return_value=manager),
        patch.object(main, "run_game_maintenance", new_callable=AsyncMock) as maintenance,
        patch.object(main, "monotonic", return_value=100) as clock,
    ):
        with TestClient(app) as client:
            client.get("/api/game/status")
            maintenance.assert_awaited_once()
            client.get("/api/matches/upcoming")
            maintenance.assert_awaited_once()
            clock.return_value = 131
            client.get("/api/game/status")
            assert maintenance.await_count == 2
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
