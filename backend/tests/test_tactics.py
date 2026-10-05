from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from bson import ObjectId
from test_game import account, create

from app.main import app
from app.models.game import utcnow
from app.repositories.game import GameRepository
from app.services.competition import CompetitionService


def setup(client):
    headers = account(client, 1)
    club = create(client, headers)
    squad = client.get("/api/squad", headers=headers).json()
    match = app.state.database.matches.find_one({"home_club_id": ObjectId(club["id"])})
    return headers, club, squad, match


def test_tactics_persistence_actual_players_and_lineup_sync(client):
    headers, club, squad, match = setup(client)
    tactics = {
        "formation": "3-4-3",
        "play_style": "all_out_attack",
        "marking": "heavy",
        "attack_focus": "wings",
    }
    response = client.put("/api/tactics", headers=headers, json=tactics)
    assert response.status_code == 200, response.text
    assert all(response.json()[key] == value for key, value in tactics.items())
    assert client.get("/api/tactics", headers=headers).json()["formation"] == "3-4-3"
    stored = app.state.database.club_tactics.find_one({"club_id": ObjectId(club["id"])})
    assert stored["updated_at"]
    updated = client.get("/api/squad", headers=headers).json()["lineup"]
    assert set(updated["starters"]) == set(squad["lineup"]["starters"])
    assert updated["formation"] == "3-4-3"
    service = CompetitionService(GameRepository(app.state.database))
    service.play(match["_id"], match["date"])
    snapshot = app.state.database.matches.find_one({"_id": match["_id"]})["result"]["snapshot"][
        "home"
    ]
    assert snapshot["style"] == "all_out_attack" and snapshot["formation"] == "3-4-3"
    assert {p["id"] for p in snapshot["lineup"]} == set(squad["lineup"]["starters"])
    assert {p["side"] for p in snapshot["lineup"]} >= {"center", "left", "right"}
    original = squad["lineup"]
    assert (
        client.put(
            "/api/squad/lineup",
            headers=headers,
            json={key: original[key] for key in ("formation", "starters", "reserves")},
        ).status_code
        == 200
    )
    assert client.get("/api/tactics", headers=headers).json()["formation"] == "4-4-2"


def test_commands_offline_history_and_temporal_snapshot(client):
    headers, club, squad, match = setup(client)
    url = f"/api/competition/matches/{match['_id']}/commands"
    tactic = {
        "minute": 45,
        "type": "tactics_change",
        "payload": {
            "marking": "heavy",
            "play_style": "all_out_attack",
            "attack_focus": "center",
            "formation": "4-3-3",
        },
    }
    sub = {
        "minute": 60,
        "type": "substitution",
        "payload": {
            "out_player_id": squad["lineup"]["starters"][1],
            "in_player_id": squad["lineup"]["reserves"][0],
        },
    }
    for command in (tactic, sub):
        response = client.post(url, headers=headers, json=command)
        assert response.status_code == 200, response.text
    service = CompetitionService(GameRepository(app.state.database))
    service.play(match["_id"], match["date"])
    result = app.state.database.matches.find_one({"_id": match["_id"]})["result"]
    assert len(result["snapshot"]["commands"]) == 2
    events = [e for e in result["events"] if e["team_id"] == club["id"]]
    assert next(e for e in events if e["type"] == "marking_change")["minute"] == 45
    assert next(
        e for e in events if e["type"] in {"substitution", "command_rejected"} and e["minute"] == 60
    )
    assert result["snapshot"]["home"]["marking"] == "light"
    assert client.post(url, headers=headers, json=tactic).status_code == 409


def test_invalid_obsolete_foreign_and_started_commands(client):
    headers, club, squad, match = setup(client)
    url = f"/api/competition/matches/{match['_id']}/commands"
    for payload in (
        {"tempo": "fast"},
        {"pressing": "high"},
        {"defensive_line": "high"},
        {"formation": "2-2-6"},
        {"marking": []},
        {},
    ):
        assert (
            client.post(
                url,
                headers=headers,
                json={"minute": 45, "type": "tactics_change", "payload": payload},
            ).status_code
            == 422
        )
    assert client.put("/api/tactics", headers=headers, json={"pressing": "high"}).status_code == 422
    assert (
        client.post(
            url,
            headers=headers,
            json={"minute": 90, "type": "tactics_change", "payload": {"marking": "heavy"}},
        ).status_code
        == 422
    )
    foreign = account(client, 2)
    foreign_club = create(client, foreign, "Outro clube")
    foreign_fixture = app.state.database.matches.find_one(
        {
            "home_club_id": ObjectId(club["id"]),
            "away_club_id": {"$ne": ObjectId(foreign_club["id"])},
        }
    )
    foreign_url = f"/api/competition/matches/{foreign_fixture['_id']}/commands"
    command = {"minute": 45, "type": "tactics_change", "payload": {"marking": "heavy"}}
    assert client.post(foreign_url, headers=foreign, json=command).status_code == 403
    assert (
        client.post(
            url,
            headers=headers,
            json={
                "minute": 45,
                "type": "substitution",
                "payload": {
                    "out_player_id": squad["lineup"]["starters"][0],
                    "in_player_id": str(ObjectId()),
                },
            },
        ).status_code
        == 422
    )
    app.state.database.matches.update_one(
        {"_id": match["_id"]}, {"$set": {"date": utcnow() - timedelta(minutes=1)}}
    )
    assert client.post(url, headers=headers, json=command).status_code == 409


def test_concurrent_substitutions_cannot_exceed_five(client):
    headers, club, squad, match = setup(client)
    url = f"/api/competition/matches/{match['_id']}/commands"

    def submit(index):
        return client.post(
            url,
            headers=headers,
            json={
                "minute": 60,
                "type": "substitution",
                "payload": {
                    "out_player_id": squad["lineup"]["starters"][index],
                    "in_player_id": squad["lineup"]["reserves"][index],
                },
            },
        ).status_code

    with ThreadPoolExecutor(max_workers=6) as executor:
        statuses = list(executor.map(submit, range(6)))
    assert statuses.count(200) == 5
    assert statuses.count(422) == 1
    assert len(app.state.database.matches.find_one({"_id": match["_id"]})["commands"]) == 5
