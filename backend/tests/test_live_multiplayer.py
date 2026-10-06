import asyncio
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException
from test_game import account, create

from app.main import app
from app.models.game import utcnow
from app.repositories.game import GameRepository
from app.services.live_match import MatchRoomManager, team_from_snapshot
from app.services.match_engine import MatchEngine


class Socket:
    def __init__(self):
        self.messages = []

    async def send_json(self, message):
        self.messages.append(deepcopy(message))


def setup(client):
    h1, h2 = account(client, 1), account(client, 2)
    c1, c2 = create(client, h1), create(client, h2)
    db = app.state.database
    home, away = ObjectId(c1["id"]), ObjectId(c2["id"])
    match = db.matches.find_one({"home_club_id": home, "away_club_id": away})
    db.matches.update_one({"_id": match["_id"]}, {"$set": {"date": utcnow()}})
    repo = GameRepository(db)
    u1 = SimpleNamespace(id=str(repo.find("clubs", {"_id": home})["owner_user_id"]))
    u2 = SimpleNamespace(id=str(repo.find("clubs", {"_id": away})["owner_user_id"]))
    return h1, h2, u1, u2, match["_id"], repo


def test_shared_room_ordered_commands_privacy_pause_and_restart(client):
    h1, h2, u1, u2, match, repo = setup(client)

    async def scenario():
        manager = MatchRoomManager(repo)
        room = await manager.get(str(match), u1, start_task=False)
        assert await manager.get(str(match), u2, start_task=False) is room
        home, away = Socket(), Socket()
        cid1, cid2 = str(room.match["home_club_id"]), str(room.match["away_club_id"])
        room.connections.update({home: (u1, cid1), away: (u2, cid2)})
        await room.start()
        assert room.session.frame["minute"] == 0 and room.session.result is None
        a, b = room.state(cid1), room.state(cid2)
        assert a["home_score"] == b["home_score"] and a["events"] == b["events"]
        assert a["own_team"]["id"] == cid1 and b["own_team"]["id"] == cid2
        with pytest.raises(HTTPException) as speed_error:
            await room.command(u1, {"type": "set_speed", "speed": 4})
        assert speed_error.value.status_code == 422
        with pytest.raises(HTTPException) as skip_error:
            await room.command(u1, {"type": "skip_to_end"})
        assert skip_error.value.status_code == 409
        await room.command(u1, {"type": "pause"})
        frozen = deepcopy(room.session.frame)
        assert room.session.advance() == frozen
        assert room.session.paused
        await room.command(u2, {"type": "resume"})
        commands = [
            {"type": "tactics_change", "command_id": "home-1", "payload": {"marking": "heavy"}},
            {
                "type": "tactics_change",
                "command_id": "away-1",
                "payload": {"attack_focus": "wings"},
            },
        ]
        submitted = await asyncio.gather(
            room.command(u1, commands[0]), room.command(u2, commands[1])
        )
        assert [r["sequence_number"] for r in submitted] == [1, 2]
        again = await room.command(u1, commands[0])
        assert again["id"] == submitted[0]["id"] and len(room.command_rows) == 2
        while room.session.frame["minute"] < 60:
            room.session.advance()
        await room.checkpoint(force=True)
        assert all(r["status"] == "applied" for r in room.command_rows)
        opponent = room.state(cid2)
        assert all(
            "value" not in e and "previous" not in e
            for e in opponent["events"]
            if e.get("team_id") == cid1 and e["type"].endswith("_change")
        )
        await room.command(
            u1,
            {
                "type": "substitution",
                "command_id": "sub-60",
                "payload": {
                    "out_player_id": room.state(cid1)["own_team"]["lineup"][-1]["id"],
                    "in_player_id": room.state(cid1)["own_team"]["reserves"][-1]["id"],
                },
            },
        )
        checkpoint = deepcopy(room.session.frame)
        resumed_manager = MatchRoomManager(repo)
        resumed = await resumed_manager.get(str(match), u2, start_task=False)
        await resumed.start()
        assert resumed.session.frame["minute"] == 60
        assert resumed.session.frame["score"] == checkpoint["score"]
        assert resumed.session.frame["events"] == checkpoint["events"]
        result = resumed.session.simulate_to_end()
        context = repo.find("match_contexts", {"_id": match})
        expected = MatchEngine().simulate(
            team_from_snapshot(context["home"]),
            team_from_snapshot(context["away"]),
            context["seed"],
            commands=[r["engine_command"] for r in resumed.command_rows],
        )
        assert result == expected
        await resumed.finish()
        await resumed.finish()
        assert repo.find("matches", {"_id": match})["status"] == "completed"
        assert repo.database.ticket_history.count_documents({"match_id": match}) == 1
        assert repo.database.match_events.count_documents({"match_id": match}) == len(
            result["events"]
        )
        assert repo.database.match_commands.count_documents({"match_id": match}) == 3
        await manager.close()
        await resumed_manager.close()

    asyncio.run(scenario())
    report = client.get(f"/api/competition/matches/{match}", headers=h1)
    assert report.status_code == 200, report.text
    assert any(e["type"] == "substitution" for e in report.json()["events"])
    assert all(
        not {"value", "previous", "command", "payload", "metadata"}.intersection(event)
        for event in report.json()["events"]
        if event.get("team_id") == str(repo.find("matches", {"_id": match})["away_club_id"])
        and event["type"].endswith("_change")
    )


def test_websocket_auth_shared_sync_and_disconnect_finishes(client):
    h1, h2, u1, u2, match, repo = setup(client)
    # Connect before kickoff so both managers receive the initial room state.
    repo.update("matches", {"_id": match}, {"$set": {"date": utcnow() + timedelta(seconds=30)}})
    with client.websocket_connect(f"/ws/matches/{match}", headers=h1) as home:
        initial = home.receive_json()
        assert initial["type"] == "participant_connected" and initial["data"]["current_minute"] == 0
        assert home.receive_json()["type"] == "sync"
        with client.websocket_connect(f"/ws/matches/{match}", headers=h2) as away:
            assert away.receive_json()["type"] == "participant_connected"
            sync = away.receive_json()
            assert sync["type"] == "sync" and sync["data"]["connected_users"] == 2
            joined = home.receive_json()
            assert joined["data"]["connected_users"] == 2
            home.send_json({"type": "heartbeat"})
            assert home.receive_json()["type"] == "sync"
            home.send_json(
                {
                    "type": "tactics_change",
                    "club_id": str(repo.find("matches", {"_id": match})["away_club_id"]),
                    "command_id": "forged",
                    "payload": {"marking": "heavy"},
                }
            )
            rejected = home.receive_json()
            assert rejected["type"] == "command_rejected"
            assert "próprio" in rejected["data"]["reason"]
        # Both leave: no client can prevent the automatic conclusion.
    room = app.state.match_rooms.rooms[str(match)]
    room.match["date"] = utcnow()
    repo.update("matches", {"_id": match}, {"$set": {"date": room.match["date"]}})

    async def finish_offline():
        for _ in range(200):
            if repo.find("matches", {"_id": match})["status"] == "completed":
                return
            await asyncio.sleep(0.05)
        raise AssertionError("The room did not finish automatically after both managers left")

    client.portal.call(finish_offline)
    assert repo.find("matches", {"_id": match})["status"] == "completed"
    assert not repo.database.match_participants.count_documents(
        {"match_id": match, "connected": True}
    )
    outsider = account(client, 3)
    create(client, outsider)
    assert client.get(f"/api/matches/{match}/live-state", headers=outsider).status_code == 403
    assert client.get(f"/api/matches/{match}/live-state").status_code == 401
    assert client.get(f"/api/matches/{match}/live-state", headers=h1).json()["status"] == "finished"


def test_live_cup_and_friendly_settle_the_same_production_result(client):
    from app.schemas.game import FriendlyInput
    from app.services.competition import CompetitionService
    from app.services.cup import CupService
    from app.services.season_calendar import FriendlyService

    h1, _, u1, _, _, repo = setup(client)
    season = CompetitionService.current(repo)
    repo.transaction(lambda tx: CupService.ensure(tx, season))
    club = repo.owned(u1.id)
    cup = repo.find(
        "competition_matches",
        {"$or": [{"home_club_id": club["_id"]}, {"away_club_id": club["_id"]}]},
    )
    if cup is None:
        first_round = repo.many(
            "competition_matches", {"status": "scheduled", "round": 1}, limit=None
        )
        for pending in first_round:
            CupService(repo).play(pending["_id"], pending["date"])
        cup = repo.find(
            "competition_matches",
            {
                "status": "scheduled",
                "$or": [{"home_club_id": club["_id"]}, {"away_club_id": club["_id"]}],
            },
        )
    assert cup, "The manager must appear in the round after a bye"
    repo.update("competition_matches", {"_id": cup["_id"]}, {"$set": {"date": utcnow()}})
    rival = repo.find("clubs", {"is_bot": True, "active": {"$ne": False}})
    friendly = FriendlyService(repo).create(
        u1,
        FriendlyInput(
            opponent_club_id=str(rival["_id"]), date=season["starts_at"] + timedelta(days=1)
        ),
    )
    repo.update("friendly_matches", {"_id": ObjectId(friendly["id"])}, {"$set": {"date": utcnow()}})

    async def play(identity, knockout):
        manager = MatchRoomManager(repo)
        room = await manager.get(str(identity), u1, start_task=False)
        await room.start()
        context = repo.find("match_contexts", {"_id": identity})
        engine = MatchEngine()
        h, a = team_from_snapshot(context["home"]), team_from_snapshot(context["away"])
        expected = (
            engine.simulate_knockout(h, a, context["seed"])
            if knockout
            else engine.simulate(h, a, context["seed"])
        )
        room.session.simulate_to_end()
        assert room.session.result == expected
        await room.finish()
        assert room.match["status"] == "completed"
        await manager.close()

    asyncio.run(play(cup["_id"], True))
    asyncio.run(play(ObjectId(friendly["id"]), False))
    assert client.get(f"/api/competition/matches/{cup['_id']}", headers=h1).status_code == 200
    report = client.get(f"/api/competition/matches/{friendly['id']}", headers=h1)
    assert report.status_code == 200, report.text
    assert report.json()["ratings"] and report.json()["financial"]["income"] >= 0
