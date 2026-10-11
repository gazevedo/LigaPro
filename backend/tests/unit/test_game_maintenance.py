import asyncio
import importlib
import os
from unittest.mock import AsyncMock, Mock, patch

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
