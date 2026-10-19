from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from pymongo.errors import NetworkTimeout, OperationFailure

from app.repositories.game import GameRepository
from app.schemas.game import ClubInput
from app.services.game import ClubService


def test_creation_database_timeout_returns_retryable_error():
    repo = Mock()
    repo.transaction.side_effect = NetworkTimeout("deadline exceeded")
    with patch("app.services.game.CompetitionService.ensure_lock"):
        with pytest.raises(HTTPException) as error:
            ClubService(repo).create(
                Mock(), ClubInput(name="123", country_id="BR", badge_id="blue", stadium_name="123")
            )
    assert error.value.status_code == 503
    assert "Tente novamente" in error.value.detail


def test_creation_does_not_hide_other_database_errors():
    repo = Mock()
    repo.transaction.side_effect = OperationFailure("database failed")
    with patch("app.services.game.CompetitionService.ensure_lock"):
        with pytest.raises(OperationFailure):
            ClubService(repo).create(
                Mock(), ClubInput(name="123", country_id="BR", badge_id="blue")
            )


@pytest.mark.parametrize("transactional", [False, True])
def test_rules_are_cached_only_inside_a_transaction(transactional):
    repo = GameRepository(Mock(), session=Mock() if transactional else None)
    repo.find = Mock(return_value={"value": {"initial_capacity": 12345}})
    first = repo.rules()
    first["initial_capacity"] = 1
    assert repo.rules()["initial_capacity"] == 12345
    assert repo.find.call_count == (1 if transactional else 2)
