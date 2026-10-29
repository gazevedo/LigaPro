import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.controllers.live import live_state


def test_slow_kickoff_keeps_one_background_refresh_and_returns_scoreboard():
    async def scenario():
        gate = asyncio.Event()
        room = SimpleNamespace(
            lock=asyncio.Lock(),
            authorize=Mock(return_value={"_id": "club"}),
            advance_clock=AsyncMock(side_effect=lambda: None),
            state=Mock(return_value={"home_name": "Casa"}),
        )

        async def slow():
            await gate.wait()

        room.advance_clock.side_effect = slow
        request = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(match_rooms=SimpleNamespace(get=AsyncMock(return_value=room)))
            )
        )
        original_wait = asyncio.wait

        async def quick_wait(tasks, **kwargs):
            return await original_wait(tasks, timeout=0.001)

        with patch("app.controllers.live.asyncio.wait", side_effect=quick_wait):
            assert (await live_state("match", request, object()))["home_name"] == "Casa"
            await live_state("match", request, object())
            assert room.advance_clock.await_count == 1
            gate.set()
            await room.state_refresh_task

    asyncio.run(scenario())
