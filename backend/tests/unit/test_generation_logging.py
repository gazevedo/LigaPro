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
    assert budgets == [3, 5, 12, 2]
    competition.return_value.initialize_universe.assert_called_once_with(max_steps=1)
    assert "event=league_committed" in caplog.text
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
    repository.update.side_effect = error
    with pytest.raises(OperationFailure) as caught:
        CompetitionService.lock(repository)
    assert caught.value is error
    assert "event=league_lock_failed" in caplog.text
    assert "code=112" in caplog.text
    assert "WriteConflict" in caplog.text
    assert "TransientTransactionError" in caplog.text
