from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.config.game import GameConfig
from app.models.game import round_match_time
from app.services.competition import CompetitionService
from mock_database import import_database


@pytest.mark.parametrize(
    "hour,minute,second,microsecond,expected",
    [
        (13, 39, 59, 123, (13, 45)),
        (13, 45, 0, 0, (13, 45)),
        (13, 45, 1, 0, (14, 0)),
        (23, 59, 59, 0, (0, 0)),
    ],
)
def test_match_times_round_forward_to_quarters(hour, minute, second, microsecond, expected):
    value = datetime(2026, 10, 20, hour, minute, second, microsecond, tzinfo=timezone.utc)
    result = round_match_time(value)
    assert (result.hour, result.minute) == expected
    assert result.second == result.microsecond == 0 and result >= value


def test_new_schedule_first_match_is_future_and_all_rounds_share_grid():
    start = datetime(2026, 10, 20, 13, 39, 27, tzinfo=timezone.utc)
    season = {
        "_id": "season",
        "starts_at": start,
        "config": GameConfig(PRESEASON_DAYS=0).snapshot(),
    }
    repo = Mock()
    with patch.object(CompetitionService, "refresh_positions"):
        CompetitionService.schedule(
            repo,
            season,
            {"_id": "division", "name": "A"},
            [{"_id": i, "club_id": i} for i in range(20)],
        )
    fixtures = repo.insert_many.call_args_list[0].args[1]
    assert len(fixtures) == 380
    assert min(row["date"] for row in fixtures) > start
    assert all(
        row["date"].minute % 15 == row["date"].second == row["date"].microsecond == 0
        for row in fixtures
    )


def test_clock_migration_preserves_overdue_matches_for_catchup():
    now = datetime(2026, 10, 20, 17, tzinfo=timezone.utc)
    original = now.replace(hour=13, minute=39, second=28)
    season = {
        "_id": "season",
        "starts_at": now - timedelta(days=1),
        "league_schedule_revision": 3,
        "league_games_per_day": 24,
    }
    repo = Mock()
    repo.rules.return_value = {}
    repo.find.return_value = season
    repo.many.side_effect = lambda collection, *a, **k: (
        [{"_id": "late", "round": 1, "date": original}] if collection == "matches" else []
    )
    with patch("app.services.competition.utcnow", return_value=now):
        CompetitionService.update_league_interval(repo)
    match_change = next(
        call.args for call in repo.update.call_args_list if call.args[0] == "matches"
    )
    assert match_change[2]["$set"]["date"] == original.replace(minute=45, second=0)
    assert match_change[2]["$set"]["date"] < now
    repo.database.calendar_events.update_many.assert_called_once()


def test_initial_import_schedules_future_matches_and_matching_calendar_events():
    now = datetime(2026, 10, 20, 13, 39, 27, tzinfo=timezone.utc)
    database = MagicMock()
    database.clubs.find_one.return_value = None
    repo = Mock()
    repo.find.side_effect = [None, None, {"started_at": now}]
    with (
        patch("mock_database.GameRepository", return_value=repo),
        patch("mock_database.utcnow", return_value=now),
    ):
        assert import_database(database)
    calls = database.__getitem__.return_value.bulk_write.call_args_list
    inserted = [operation._doc["$setOnInsert"] for call in calls for operation in call.args[0]]
    fixtures = {row["_id"]: row for row in inserted if "home_slot_id" in row and "date" in row}
    assert len(fixtures) == 380
    assert min(row["date"] for row in fixtures.values()) > now
    assert all(
        row["date"].minute % 15 == row["date"].second == row["date"].microsecond == 0
        for row in fixtures.values()
    )
    events = [row for row in inserted if row.get("reference_id") in fixtures]
    assert len(events) == 760
    assert all(row["date"] == fixtures[row["reference_id"]]["date"] for row in events)
