"""Wake for the next persisted fixture, independently of screen requests."""

import asyncio
import logging

from app.models.game import utcnow

logger = logging.getLogger(__name__)
MATCH_COLLECTIONS = ("matches", "competition_matches", "friendly_matches")


def next_game_delay(repository, now=None, max_idle=30):
    dates = []
    for collection in MATCH_COLLECTIONS:
        rows = repository.many(
            collection,
            {"status": "scheduled"},
            limit=1,
            sort=[("date", 1)],
            projection={"date": 1},
        )
        if rows:
            dates.append(rows[0]["date"])
    if not dates:
        return max_idle
    # Recheck periodically for newly scheduled fixtures. A due fixture which is
    # temporarily busy must not cause a tight retry loop.
    remaining = (min(dates) - (now or utcnow())).total_seconds()
    return min(max_idle, remaining) if remaining > 0 else 1


async def run_game_scheduler(repository, operation, stop=None):
    stop = stop or asyncio.Event()
    while not stop.is_set():
        delay = 5
        try:
            logger.info("game_job event=running")
            await operation()
            if stop.is_set():
                break
            delay = await asyncio.to_thread(next_game_delay, repository)
            logger.info("game_job event=waiting seconds=%s", delay)
        except Exception:
            logger.exception("game_job event=failed retry_seconds=%s", delay)
        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
        except TimeoutError:
            pass
