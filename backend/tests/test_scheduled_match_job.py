from types import SimpleNamespace
from unittest.mock import patch

import pytest
from bson import ObjectId

from app.main import app
from app.repositories.game import GameRepository
from app.schemas.game import ClubInput
from app.services.game import ClubService
from mock_database import import_database
from run_scheduled_matches import run_once


def test_external_tick_finishes_round_with_human_club_without_http_or_lifespan(client):
    database = app.state.database
    import_database(database)
    repo = GameRepository(database)
    club = ClubService(repo).create(
        SimpleNamespace(id=str(ObjectId())),
        ClubInput(name="Clube humano", country_id="BR", badge_id="blue"),
    )
    now = database.matches.find_one(sort=[("date", 1)])["date"]
    with (
        patch("run_scheduled_matches.utcnow", return_value=now),
        patch("app.services.game.utcnow", return_value=now),
    ):
        first = run_once(database)
        second = run_once(database)
    assert first == {"completed_matches": 10, "due_before": 10, "remaining_due": 0}
    assert second == {"completed_matches": 0, "due_before": 0, "remaining_due": 0}
    assert database.matches.count_documents({"status": "completed"}) == 10
    assert sum(row["games"] for row in database.standings.find()) == 20
    identity = ObjectId(club["id"])
    assert (
        database.matches.count_documents(
            {"status": "completed", "$or": [{"home_club_id": identity}, {"away_club_id": identity}]}
        )
        == 1
    )
    assert database.game_state.find_one({"_id": "scheduled_match_job"})["status"] == "completed"


def test_external_tick_refuses_an_unprepared_database(client):
    with pytest.raises(RuntimeError, match="ainda não está pronta"):
        run_once(app.state.database)


def test_external_tick_records_processing_failure(client):
    database = app.state.database
    import_database(database)
    with patch("run_scheduled_matches.process_due", side_effect=RuntimeError("failure")):
        with pytest.raises(RuntimeError, match="failure"):
            run_once(database)
    state = database.game_state.find_one({"_id": "scheduled_match_job"})
    assert state["status"] == "failed" and state["error_type"] == "RuntimeError"


def test_external_tick_does_not_report_success_when_due_matches_make_no_progress(client):
    database = app.state.database
    import_database(database)
    now = database.matches.find_one(sort=[("date", 1)])["date"]
    with (
        patch("run_scheduled_matches.utcnow", return_value=now),
        patch("run_scheduled_matches.process_due"),
    ):
        with pytest.raises(RuntimeError, match="nenhum foi concluído"):
            run_once(database)
    assert database.game_state.find_one({"_id": "scheduled_match_job"})["status"] == "failed"


def test_calendar_migration_batches_writes_and_preserves_finished_and_live_games(client):
    from datetime import timedelta

    from pymongo.synchronous.collection import Collection

    from app.services.competition import CompetitionService

    database = app.state.database
    import_database(database)
    fixtures = list(database.matches.find().sort("date", 1))
    completed, live = fixtures[:2]
    database.matches.update_one({"_id": completed["_id"]}, {"$set": {"status": "completed"}})
    database.matches.update_one({"_id": live["_id"]}, {"$set": {"status": "live"}})
    # Reproduce an existing calendar that still needs the clock migration.
    database.matches.update_many(
        {"status": "scheduled"},
        [{"$set": {"date": {"$dateAdd": {"startDate": "$date", "unit": "second", "amount": 443}}}}],
    )
    preserved = list(database.matches.find({"status": {"$in": ["completed", "live"]}}))
    calls = []
    original = Collection.bulk_write

    def record(collection, requests, *args, **kwargs):
        calls.append((collection.name, len(requests)))
        return original(collection, requests, *args, **kwargs)

    repo = GameRepository(database)
    now = fixtures[0]["date"] + timedelta(hours=2)
    with (
        patch.object(Collection, "bulk_write", record),
        patch("app.services.competition.utcnow", return_value=now),
    ):
        repo.transaction(CompetitionService.update_league_interval)
    assert [name for name, _ in calls] == ["matches", "calendar_events"]
    assert all(count <= 38 for _, count in calls)
    assert list(database.matches.find({"status": {"$in": ["completed", "live"]}})) == preserved
    scheduled = list(database.matches.find({"status": "scheduled"}))
    assert len(scheduled) == 378
    assert all(
        row["date"].minute % 15 == row["date"].second == row["date"].microsecond == 0
        for row in scheduled
    )
    dates = {row["_id"]: row["date"] for row in scheduled}
    events = database.calendar_events.find({"reference_id": {"$in": list(dates)}})
    assert all(row["date"] == dates[row["reference_id"]] for row in events)
    assert database.seasons.find_one({"status": "active"})["league_schedule_revision"] == 4
