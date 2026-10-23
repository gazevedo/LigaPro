from datetime import timedelta
from unittest.mock import patch

from test_game import account, create

from app.main import app
from mock_database import import_database


def test_live_http_resumes_across_instances_and_settles_once_after_five_minutes(client):
    from app.repositories.game import GameRepository
    from app.services.live_match import MatchRoomManager

    db = app.state.database
    import_database(db)
    headers = account(client, 1)
    club = create(client, headers)
    fixture = db.matches.find_one(sort=[("date", 1)])
    # Choose the human club's fixture in the first round.
    from bson import ObjectId

    fixture = db.matches.find_one(
        {
            "round": 1,
            "$or": [{"home_club_id": ObjectId(club["id"])}, {"away_club_id": ObjectId(club["id"])}],
        }
    )
    identity, kickoff = fixture["_id"], fixture["date"]
    path = f"/api/matches/{identity}/live-state"
    for seconds, expected in [(0, 0), (150, 45), (299, 89.7), (300, 90)]:
        # Discard all in-memory state to reproduce separate Vercel invocations.
        app.state.match_rooms = MatchRoomManager(GameRepository(db))
        with patch(
            "app.services.live_match.utcnow", return_value=kickoff + timedelta(seconds=seconds)
        ):
            response = client.get(path, headers=headers)
        assert response.status_code == 200, response.text
        state = response.json()
        assert abs(state["current_minute"] - expected) < 0.01
        assert all(event["minute"] <= state["current_minute"] for event in state["events"])
        if seconds == 150:
            with patch(
                "app.services.live_match.utcnow", return_value=kickoff + timedelta(seconds=seconds)
            ):
                command = client.post(
                    f"/api/matches/{identity}/commands/combined_change",
                    headers=headers,
                    json={"command_id": "cold-instance-command", "payload": {"marking": "heavy"}},
                )
            assert command.status_code == 200, command.text
        if seconds == 299:
            assert state["own_team"]["marking"] == "heavy"
        if seconds < 300:
            assert state["status"] != "finished"
            assert db.matches.find_one({"_id": identity})["status"] == "live"
            assert sum(r["games"] for r in db.standings.find()) == 0
        else:
            assert state["status"] == "finished"
            assert sum(r["games"] for r in db.standings.find()) == 2
    with patch("app.services.live_match.utcnow", return_value=kickoff + timedelta(minutes=6)):
        assert client.get(path, headers=headers).json()["status"] == "finished"
    assert sum(r["games"] for r in db.standings.find()) == 2


def test_scheduler_keeps_recent_games_live_without_any_connected_user(client):
    from app.repositories.game import GameRepository
    from app.services.competition import CompetitionService

    db = app.state.database
    import_database(db)
    repo = GameRepository(db)
    fixture = db.matches.find_one(sort=[("date", 1)])
    kickoff = fixture["date"]
    service = CompetitionService(repo)
    now = kickoff + timedelta(minutes=2)
    with patch("app.services.live_match.utcnow", return_value=now):
        service.process_due(now, max_matches=1)
    live = db.matches.find_one({"status": "live"})
    assert live and live["live_minute"] == 35
    assert "result" not in live
    assert sum(row["games"] for row in db.standings.find()) == 0
    assert db.match_participants.count_documents({}) == 0
    now = kickoff + timedelta(minutes=5)
    with patch("app.services.live_match.utcnow", return_value=now):
        service.process_due(now, max_matches=0)
    assert db.matches.find_one({"_id": live["_id"]})["status"] == "completed"
    assert sum(row["games"] for row in db.standings.find()) == 2
