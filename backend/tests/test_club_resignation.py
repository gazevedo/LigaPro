from bson import ObjectId
from test_game import account, create

from app.main import app
from app.repositories.game import GameRepository
from app.services.competition import CompetitionService


def test_resignation_requires_confirmation_and_owner(client):
    owner, outsider = account(client, 1), account(client, 2)
    club = create(client, owner)
    path = f"/api/clubs/{club['id']}/resign"
    assert client.post(path, json={"confirmed": True}).status_code == 401
    assert client.post(path, headers=owner, json={}).status_code == 422
    assert client.post(path, headers=owner, json={"confirmed": False}).status_code == 422
    assert client.post(path, headers=outsider, json={"confirmed": True}).status_code == 403
    assert client.get("/api/game/status", headers=owner).json()["club"]["id"] == club["id"]


def test_resignation_inactivates_and_new_club_inherits_no_assets(client):
    owner = account(client, 1)
    club = create(client, owner)
    db = app.state.database
    old = ObjectId(club["id"])
    db.club_finances.update_one({"_id": old}, {"$set": {"balance": 987654321}})
    players = set(p["_id"] for p in db.players.find({"owner_club_id": old}))
    player = next(
        p
        for p in db.players.find({"owner_club_id": old})
        if p["_id"] in db.lineups.find_one({"_id": old})["reserves"]
    )
    listing = client.post(
        "/api/market/listings",
        headers=owner,
        json={"player_id": str(player["_id"]), "type": "sale", "price": 100000, "duration_days": 1},
    )
    assert listing.status_code == 201, listing.text
    path = f"/api/clubs/{club['id']}/resign"
    response = client.post(path, headers=owner, json={"confirmed": True})
    assert response.status_code == 200 and response.json() == {"club": None}
    archived = db.clubs.find_one({"_id": old})
    assert archived["active"] is False and archived["owner_user_id"] is None
    assert not archived.get("is_bot")
    assert db.club_finances.find_one({"_id": old})["balance"] == 987654321
    assert (
        db.transfer_listings.find_one({"_id": ObjectId(listing.json()["id"])})["status"]
        == "cancelled"
    )
    assert CompetitionService.match_team(GameRepository(db), old) is None
    assert client.get("/api/game/status", headers=owner).json() == {"club": None}
    assert client.get("/api/squad", headers=owner).status_code == 403
    new = create(client, owner, "Clube novo")
    assert new["id"] != club["id"]
    assert client.get("/api/finance", headers=owner).json()["balance"] == 10000000
    assert players.isdisjoint(
        p["_id"] for p in db.players.find({"owner_club_id": ObjectId(new["id"])})
    )
    # Retrying the previous club's request must never inactivate the newly created club.
    assert client.post(path, headers=owner, json={"confirmed": True}).status_code == 403
    assert client.get("/api/game/status", headers=owner).json()["club"]["id"] == new["id"]


def test_resignation_waits_for_live_match(client):
    owner = account(client, 1)
    club = create(client, owner)
    db = app.state.database
    match = db.matches.find_one({"home_club_id": ObjectId(club["id"])})
    db.matches.update_one({"_id": match["_id"]}, {"$set": {"status": "live"}})
    response = client.post(
        f"/api/clubs/{club['id']}/resign", headers=owner, json={"confirmed": True}
    )
    assert response.status_code == 409
    assert client.get("/api/game/status", headers=owner).json()["club"]["id"] == club["id"]
    db.matches.update_one({"_id": match["_id"]}, {"$set": {"status": "scheduled"}})


def test_inactive_club_is_replaced_by_new_bot_next_season(client):
    from app.services.competition import SeasonFinalizationService

    owner = account(client, 1)
    club = create(client, owner)
    db = app.state.database
    assert (
        client.post(
            f"/api/clubs/{club['id']}/resign", headers=owner, json={"confirmed": True}
        ).status_code
        == 200
    )
    season = db.seasons.find_one({"status": "active"})
    # Completed fixtures are irrelevant to the enrollment rule under test.
    for collection in ("matches", "competition_matches", "friendly_matches"):
        db[collection].update_many({"season_id": season["_id"]}, {"$set": {"status": "completed"}})
    db.competitions.update_many({"season_id": season["_id"]}, {"$set": {"status": "completed"}})
    SeasonFinalizationService(GameRepository(db)).finalize(season["_id"], season["ends_at"])
    upcoming = db.seasons.find_one({"status": "active"})
    assert upcoming["_id"] != season["_id"]
    slots = list(db.season_clubs.find({"season_id": upcoming["_id"]}))
    assert len(slots) == 20
    assert all(slot["club_id"] != ObjectId(club["id"]) for slot in slots)
    assert all(slot["is_bot"] for slot in slots)
    assert db.clubs.find_one({"_id": ObjectId(club["id"])})["active"] is False
