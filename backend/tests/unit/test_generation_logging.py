from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from pymongo.errors import ExecutionTimeout, OperationFailure

from app.services.competition import CompetitionService
from app.services.health import HealthService


def test_league_has_own_budget_and_reports_committed_progress(caplog):
    budgets = []

    @contextmanager
    def budget(seconds):
        budgets.append(seconds)
        yield

    progress = {
        "status": "initializing",
        "initialization": {
            "stage": "clubs",
            "percentage": 71,
            "completed_steps": 49,
            "total_steps": 69,
            "current_step": "Criar clube bot 2 de 20",
        },
    }
    with (
        patch("app.services.health.GameRepository") as repository,
        patch("app.services.health.CompetitionService") as competition,
        patch("app.services.health.timeout", budget),
        patch.object(HealthService, "progress", return_value=progress),
        caplog.at_level("INFO"),
    ):
        repository.return_value.initialize.return_value = True
        competition.return_value.initialize_universe.return_value = None
        assert HealthService(MagicMock()).check() == progress
    assert budgets == [3, 5, 12, 1, 2]
    competition.return_value.initialize_universe.assert_called_once_with(max_steps=1)
    assert "event=league_finished" in caplog.text
    assert "percentage=71" in caplog.text


def test_timeout_is_logged_and_keeps_last_committed_progress(caplog):
    progress = {
        "initialization": {
            "stage": "clubs",
            "percentage": 69,
            "completed_steps": 48,
            "total_steps": 69,
            "current_step": "Criar clube bot 1 de 20",
        }
    }
    with (
        patch("app.services.health.GameRepository") as repository,
        patch("app.services.health.CompetitionService") as competition,
        patch.object(HealthService, "progress", return_value=progress),
    ):
        repository.return_value.initialize.return_value = True
        competition.return_value.initialize_universe.side_effect = ExecutionTimeout("step expired")
        assert HealthService(MagicMock()).check() == progress
    assert "event=timeout" in caplog.text
    assert "ExecutionTimeout" in caplog.text


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


def test_busy_generation_returns_without_starting_another_transaction(caplog):
    from pymongo.errors import DuplicateKeyError

    database, competition = MagicMock(), MagicMock()
    database.game_state.find_one_and_update.side_effect = DuplicateKeyError("lease owned")
    with caplog.at_level("INFO"):
        assert HealthService(database).advance_league(competition, "second") is None
    competition.initialize_universe.assert_not_called()
    database.game_state.delete_one.assert_not_called()
    assert "event=busy" in caplog.text


def test_generation_releases_only_its_own_lease_after_failure():
    database, competition = MagicMock(), MagicMock()
    competition.initialize_universe.side_effect = ExecutionTimeout("expired")
    with pytest.raises(ExecutionTimeout):
        HealthService(database).advance_league(competition, "first")
    database.game_state.delete_one.assert_called_once_with(
        {"_id": "database_generation_lease", "owner": "first"}
    )


def test_lock_uses_update_without_reading_document_back():
    repository = MagicMock()
    CompetitionService.lock(repository)
    repository.database.game_state.update_one.assert_called_once_with(
        {"_id": "universe"}, {"$inc": {"revision": 1}}, session=repository.session
    )
    repository.update.assert_not_called()


def test_release_failure_does_not_hide_original_transaction_error(caplog):
    database, competition = MagicMock(), MagicMock()
    original = ExecutionTimeout("original transaction timeout")
    competition.initialize_universe.side_effect = original
    database.game_state.delete_one.side_effect = ExecutionTimeout("release timeout")
    with pytest.raises(ExecutionTimeout) as caught:
        HealthService(database).advance_league(competition, "owner")
    assert caught.value is original
    assert "event=lease_release_failed" in caplog.text


def test_release_budget_is_outside_generation_timeout():
    active = []

    @contextmanager
    def budget(seconds):
        active.append(seconds)
        try:
            yield
        finally:
            active.pop()

    database, competition = MagicMock(), MagicMock()

    def generation(**kwargs):
        assert active == [12]
        raise ExecutionTimeout("generation expired")

    def release(query):
        assert active == [1]

    competition.initialize_universe.side_effect = generation
    database.game_state.delete_one.side_effect = release
    with patch("app.services.health.timeout", budget), pytest.raises(ExecutionTimeout):
        HealthService(database).advance_league(competition, "owner")
    database.game_state.delete_one.assert_called_once()
