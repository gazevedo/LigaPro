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
