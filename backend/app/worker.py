"""Continuous scheduled match worker. Run: python -m app.worker."""

import asyncio
import logging
import signal

from app.config.settings import get_settings
from app.core.logging import configure_logging
from app.database.mongo import create_client
from app.repositories.game import GameRepository
from app.services.game import process_due
from app.services.game_scheduler import run_game_scheduler
from app.services.push_notifications import send_match_reminders


async def run_worker(stop=None):
    from mock_database import import_database

    stop = stop or asyncio.Event()
    loop = asyncio.get_running_loop()
    config = get_settings()
    client = create_client(config)
    signals = {}
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous = signal.getsignal(signum)
            try:
                loop.add_signal_handler(signum, stop.set)
                signals[signum] = previous
            except NotImplementedError:
                pass
        database = client[config.mongodb_database_name]
        await asyncio.to_thread(import_database, database)
        repository = GameRepository(database)

        async def execute():
            for name, operation in (
                ("matches", lambda: process_due(repository)),
                ("reminders", lambda: send_match_reminders(repository, config)),
            ):
                try:
                    await asyncio.to_thread(operation)
                except Exception:
                    logging.getLogger(__name__).exception("game_job stage=%s event=failed", name)
                    if name == "matches":
                        raise

        await run_game_scheduler(repository, execute, stop)
    finally:
        client.close()
        for signum, previous in signals.items():
            loop.remove_signal_handler(signum)
            signal.signal(signum, previous)


def main():
    configure_logging()
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
