from bson import ObjectId

from app.main import app
from tests.test_game import account, create


def test_squad_includes_contract_and_career_statistics(client):
    headers = account(client, 1)
    create(client, headers)
    squad = client.get("/api/squad", headers=headers).json()
    player_id = ObjectId(squad["players"][0]["id"])
    app.state.database.player_career_stats.insert_one(
        {
            "_id": player_id,
            "matches": 12,
            "goals": 4,
            "minutes": 980,
            "yellow_cards": 2,
            "red_cards": 1,
        }
    )
    response = client.get("/api/squad", headers=headers)
    assert response.status_code == 200
    players = response.json()["players"]
    assert len(players) == 25
    assert all(player["contract"]["expires_at"] for player in players)
    assert all(player["contract"]["salary"] == player["salary"] for player in players)
    assert players[0]["statistics"]["goals"] == 4
    assert players[0]["statistics"]["matches"] == 12


def test_competition_rankings_separate_league_cup_and_other_divisions(client):
    headers = account(client, 1)
    club = create(client, headers)
    db = app.state.database
    season = db.seasons.find_one({"status": "active"})
    slot = db.season_clubs.find_one({"season_id": season["_id"], "club_id": ObjectId(club["id"])})
    player = db.players.find_one({"current_club_id": ObjectId(club["id"])})
    cup = db.competitions.find_one({"season_id": season["_id"], "name": "Copa Nacional"})
    if not cup:
        cup = {"_id": ObjectId(), "season_id": season["_id"], "name": "Copa Nacional"}
        db.competitions.insert_one(cup)
    for collection, fields, goals in [
        ("matches", {"season_id": season["_id"], "division_id": slot["division_id"]}, 2),
        ("matches", {"season_id": season["_id"], "division_id": ObjectId()}, 50),
        ("competition_matches", {"competition_id": cup["_id"]}, 7),
    ]:
        match_id = ObjectId()
        db[collection].insert_one({"_id": match_id, **fields, "status": "completed"})
        db.player_match_ratings.insert_one(
            {
                "match_id": match_id,
                "player_id": player["_id"],
                "minutes": 90,
                "events_summary": {"goals": goals, "yellow_cards": 1, "red_cards": 0},
            }
        )
    for kind, goals in [("league", 2), ("cup", 7)]:
        response = client.get(f"/api/competition/statistics?kind={kind}", headers=headers)
        assert response.status_code == 200, response.text
        rows = response.json()["rows"]
        assert len(rows) == 1
        assert rows[0]["total"] == goals
        assert rows[0]["matches"] == 1
    assert (
        client.get("/api/competition/statistics?kind=invalid", headers=headers).status_code == 422
    )
    assert client.get("/api/competition/statistics").status_code == 401
