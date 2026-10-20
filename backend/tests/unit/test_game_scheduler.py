import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from app.services.game_scheduler import next_game_delay, run_game_scheduler


def test_next_fixture_wakes_job_at_its_time_across_all_competitions():
    now = datetime(2026, 10, 20, tzinfo=timezone.utc)
    repository = Mock()
    repository.many.side_effect = [
        [{"date": now + timedelta(seconds=20)}],
        [{"date": now + timedelta(seconds=4)}],
        [{"date": now + timedelta(seconds=10)}],
    ]
    assert next_game_delay(repository, now) == 4
    assert [call.args[0] for call in repository.many.call_args_list] == [
        "matches",
        "competition_matches",
        "friendly_matches",
    ]
    for call in repository.many.call_args_list:
        assert call.args[1] == {"status": "scheduled"}
        assert call.kwargs["limit"] == 1


def test_empty_calendar_and_far_fixtures_are_rechecked_without_busy_loop():
    repository = Mock()
    repository.many.return_value = []
    assert next_game_delay(repository) == 30
    repository.many.return_value = [{"date": datetime.now(timezone.utc) + timedelta(hours=2)}]
    assert next_game_delay(repository) == 30
    repository.many.return_value = [{"date": datetime.now(timezone.utc) - timedelta(seconds=2)}]
    assert next_game_delay(repository) == 1


def test_job_executes_without_an_http_request_and_waits_for_next_fixture():
    async def scenario():
        stop = asyncio.Event()
        operation = AsyncMock()
        waits = []

        async def wait(awaitable, timeout):
            waits.append(timeout)
            awaitable.close()
            stop.set()

        with (
            patch("app.services.game_scheduler.next_game_delay", return_value=7),
            patch("app.services.game_scheduler.asyncio.wait_for", side_effect=wait),
        ):
            await run_game_scheduler(Mock(), operation, stop)
        operation.assert_awaited_once()
        assert waits == [7]

    asyncio.run(scenario())


def test_job_retries_after_failure_and_keeps_running():
    async def scenario():
        stop = asyncio.Event()
        calls = 0

        async def operation():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("temporary database failure")
            stop.set()

        async def wait(awaitable, timeout):
            awaitable.close()
            assert timeout == 5
            raise TimeoutError

        with patch("app.services.game_scheduler.asyncio.wait_for", side_effect=wait):
            await run_game_scheduler(Mock(), operation, stop)
        assert calls == 2

    asyncio.run(scenario())


def test_worker_starts_scheduler_and_processes_matches_without_web_server():
    from app import worker

    async def scenario():
        stop = asyncio.Event()
        client = MagicMock()
        config = Mock(mongodb_database_name="game")

        async def schedule(repository, operation, received_stop):
            assert received_stop is stop
            await operation()
            stop.set()

        with (
            patch.object(worker, "get_settings", return_value=config),
            patch.object(worker, "create_client", return_value=client),
            patch("mock_database.import_database") as importer,
            patch.object(worker, "process_due") as process,
            patch.object(worker, "send_match_reminders") as reminders,
            patch.object(worker, "run_game_scheduler", side_effect=schedule),
        ):
            await worker.run_worker(stop)
        importer.assert_called_once()
        process.assert_called_once()
        reminders.assert_called_once()
        client.close.assert_called_once()

    asyncio.run(scenario())


def test_near_fixture_keeps_fractional_delay_instead_of_starting_late():
    now = datetime(2026, 10, 20, tzinfo=timezone.utc)
    repository = Mock()
    repository.many.side_effect = [[{"date": now + timedelta(milliseconds=250)}], [], []]
    assert next_game_delay(repository, now) == 0.25


def test_scheduler_discovers_new_fixture_and_executes_only_when_due():
    async def scenario():
        now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        stop = asyncio.Event()
        repository = Mock()
        fixtures = []
        completed = []
        waits = []

        def upcoming(collection, query, **kwargs):
            return [{"date": min(fixtures)}] if collection == "matches" and fixtures else []

        repository.many.side_effect = upcoming

        async def process():
            due = [date for date in fixtures if date <= now]
            for date in due:
                fixtures.remove(date)
                completed.append(date)
            if completed:
                stop.set()

        async def wait(awaitable, timeout):
            nonlocal now
            awaitable.close()
            waits.append(timeout)
            assert completed == []
            if len(waits) == 1:
                # A new fixture is saved while the scheduler waits on an empty calendar.
                fixtures.append(now + timedelta(seconds=35))
            now += timedelta(seconds=timeout)
            raise TimeoutError

        with (
            patch("app.services.game_scheduler.utcnow", side_effect=lambda: now),
            patch("app.services.game_scheduler.asyncio.wait_for", side_effect=wait),
        ):
            await run_game_scheduler(repository, process, stop)
        assert waits == [30, 5]
        assert completed == [now]

    asyncio.run(scenario())
