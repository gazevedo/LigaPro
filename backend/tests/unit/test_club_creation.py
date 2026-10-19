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


def test_ranking_refresh_does_not_rewrite_unchanged_clubs():
    from app.services.club_prestige import ClubRankingService

    identity = "club"
    repo = Mock()
    row = {"club_id": identity, "position": 1, "points": 3}
    points = ClubRankingService.points({}, row, 0)
    repo.many.side_effect = [
        [row],
        [{"_id": identity, "ranking_points": points, "ranking_position": 1, "ranking": points}],
    ]
    ClubRankingService.refresh(repo, "season")
    repo.database.clubs.bulk_write.assert_not_called()
    repo.update.assert_not_called()


def test_existing_record_is_not_written_when_new_value_does_not_beat_it():
    from app.services.game_history import HistoryService

    repo = Mock()
    repo.find.return_value = {"value": 100}
    HistoryService.record(repo, "highest_market_value", 90, "player")
    repo.database.game_records.find_one_and_update.assert_not_called()


@pytest.mark.parametrize("owner_conflict", [True, False])
def test_only_duplicate_owner_is_reported_as_already_having_a_club(owner_conflict):
    from pymongo.errors import DuplicateKeyError

    repo = Mock()
    error = DuplicateKeyError(
        "duplicate key",
        details={
            "keyPattern": {"owner_user_id" if owner_conflict else "_id": 1},
        },
    )
    repo.transaction.side_effect = error
    with pytest.raises(HTTPException if owner_conflict else DuplicateKeyError) as caught:
        ClubService(repo).create(Mock(), ClubInput(name="Clube", country_id="BR", badge_id="blue"))
    if owner_conflict:
        assert caught.value.status_code == 409
    else:
        assert caught.value is error
