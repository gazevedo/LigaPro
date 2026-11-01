import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from bson import ObjectId

from app.models.game import utcnow
from app.services.live_match import MATCH_COLLECTIONS, MatchRoomManager


@pytest.mark.parametrize("collection", MATCH_COLLECTIONS)
def test_status_read_recovers_only_the_due_fixture_of_the_authenticated_club(collection):
    async def scenario():
        now = utcnow()
        identity, club_id = ObjectId(), ObjectId()
        repo = Mock()
        repo.owned.return_value = {"_id": ObjectId()}
        repo.owned.return_value = {"_id": club_id}
        repo.many.side_effect = lambda name, *args, **kwargs: (
            [{"_id": identity, "date": now - timedelta(minutes=1)}] if name == collection else []
        )
        manager = MatchRoomManager(repo)
        room = SimpleNamespace(refresh_clock=AsyncMock())
        manager.get = AsyncMock(return_value=room)
        user = SimpleNamespace(id=ObjectId())
        with patch("app.services.live_match.utcnow", return_value=now):
            await manager.refresh_due_for_user(user)
        manager.get.assert_awaited_once_with(str(identity), user, start_task=False)
        room.refresh_clock.assert_awaited_once()
        for call in repo.many.call_args_list:
            query = call.args[1]
            assert query["date"] == {"$lte": now}
            assert query["$or"] == [{"home_club_id": club_id}, {"away_club_id": club_id}]
            assert query["status"] == {"$in": ["scheduled", "live"]}
            assert call.kwargs["limit"] == 1

    asyncio.run(scenario())


def test_future_matches_are_not_started_by_opening_the_screen():
    async def scenario():
        repo = Mock()
        repo.owned.return_value = {"_id": ObjectId()}
        repo.many.return_value = []
        manager = MatchRoomManager(repo)
        manager.get = AsyncMock()
        await manager.refresh_due_for_user(SimpleNamespace(id=ObjectId()))
        manager.get.assert_not_awaited()

    asyncio.run(scenario())


def test_recovery_resolves_the_oldest_due_fixture_before_an_overlapping_one():
    async def scenario():
        now = utcnow()
        first, second = ObjectId(), ObjectId()
        repo = Mock()
        repo.owned.return_value = {"_id": ObjectId()}
        repo.many.side_effect = [
            [{"_id": second, "date": now}],
            [{"_id": first, "date": now - timedelta(minutes=10)}],
            [],
        ]
        manager = MatchRoomManager(repo)
        manager.get = AsyncMock(return_value=SimpleNamespace(refresh_clock=AsyncMock()))
        user = SimpleNamespace(id=ObjectId())
        await manager.refresh_due_for_user(user)
        manager.get.assert_awaited_once_with(str(first), user, start_task=False)

    asyncio.run(scenario())
