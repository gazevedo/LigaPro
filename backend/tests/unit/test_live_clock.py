import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from bson import ObjectId
from test_match_engine import team

from app.models.game import utcnow
from app.services.live_match import LiveMatchSession, MatchRoom


@pytest.mark.parametrize(
    "seconds,minute,finished",
    [(0, 0, False), (149, 40, False), (150, 45, False), (299, 85, False), (300, 90, True)],
)
def test_five_minute_clock_does_not_fast_forward_without_an_audience(seconds, minute, finished):
    async def scenario():
        kickoff = utcnow()
        match = {"_id": ObjectId(), "status": "live", "date": kickoff}
        repo = Mock()
        repo.find.return_value = match
        room = MatchRoom(SimpleNamespace(repo=repo), match)

        async def recover():
            room.session = LiveMatchSession(team("h"), team("a"), 123)

        room.start = recover
        room.checkpoint = AsyncMock()
        room.finish = AsyncMock()
        await room.advance_clock(kickoff + timedelta(seconds=seconds))
        assert not room.connections
        assert room.session.frame["minute"] == minute
        assert (room.session.result is not None) is finished
        assert room.finish.await_count == int(finished)

    asyncio.run(scenario())


def test_closed_match_is_read_without_replaying_or_settling_again():
    async def scenario():
        match = {"_id": ObjectId(), "status": "completed", "date": utcnow()}
        repo = Mock()
        repo.find.return_value = match
        room = MatchRoom(SimpleNamespace(repo=repo), match)
        with patch.object(room, "start", new_callable=AsyncMock) as start:
            await room.advance_clock()
        start.assert_not_awaited()
        assert room.session is None

    asyncio.run(scenario())
