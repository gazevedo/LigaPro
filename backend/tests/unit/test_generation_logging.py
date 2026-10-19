from unittest.mock import MagicMock

import pytest
from pymongo.errors import OperationFailure

from app.services.competition import CompetitionService


def test_lock_logs_original_transient_error_before_driver_retry(caplog):
    repository = MagicMock()
    error = OperationFailure(
        "transaction aborted",
        112,
        {
            "codeName": "WriteConflict",
            "errmsg": "transaction aborted",
            "errorLabels": ["TransientTransactionError"],
        },
    )
    repository.database.game_state.update_one.side_effect = error
    with pytest.raises(OperationFailure) as caught:
        CompetitionService.lock(repository)
    assert caught.value is error
    assert "event=league_lock_failed" in caplog.text
    assert "code=112" in caplog.text
    assert "WriteConflict" in caplog.text
    assert "TransientTransactionError" in caplog.text


def test_lock_uses_update_without_reading_document_back():
    repository = MagicMock()
    CompetitionService.lock(repository)
    repository.database.game_state.update_one.assert_called_once_with(
        {"_id": "universe"}, {"$inc": {"revision": 1}}, session=repository.session
    )
    repository.update.assert_not_called()


def test_server_startup_only_pings_database():
    from unittest.mock import patch

    from test_game_maintenance import module

    initialize_database = module().initialize_database

    database = MagicMock()
    with patch("app.repositories.game.GameRepository.initialize", side_effect=AssertionError):
        initialize_database(database)
    database.command.assert_called_once_with("ping")
    database.clubs.assert_not_called()
