from bson import ObjectId

from app.config.stadium import STADIUM_LEVELS
from app.main import app
from app.repositories.game import GameRepository
from app.services.fan_base import FanBaseService


def create(client):
    response = client.post(
        "/api/clubs", json={"name": "Clube Arena", "country_id": "BR", "badge_id": "blue"}
    )
    assert response.status_code == 201
    return ObjectId(response.json()["id"])


def test_sector_prices_and_unavailable_sectors_are_validated(authenticated_client):
    client = authenticated_client
    identity = create(client)
    data = client.get("/api/stadium").json()
    assert data["arena_level"] == 1 and sum(s["capacity"] for s in data["sectors"]) == 10000
    assert len(data["levels"]) == 6
    assert client.put("/api/stadium/sectors/skybox/price", json={"price": 5000}).status_code == 409
    assert client.put("/api/stadium/sectors/invalid/price", json={"price": 5000}).status_code == 404
    assert (
        client.put("/api/stadium/sectors/lower_north/price", json={"price": -1}).status_code == 422
    )
    changed = client.put("/api/stadium/sectors/lower_north/price", json={"price": 3500})
    assert changed.status_code == 200
    values = {s["id"]: s["price"] for s in changed.json()["sectors"]}
    assert values["lower_north"] == 3500 and values["lower_south"] == 2000
    assert (
        app.state.database.stadiums.find_one({"_id": identity})["sector_prices"]["lower_north"]
        == 3500
    )
    assert client.put("/api/finance/tickets", json={"price": 2500}).status_code == 200
    assert all(s["price"] == 2500 for s in client.get("/api/stadium").json()["sectors"])


def test_arena_evolution_preserves_balance_on_failure_and_unlocks_tiers(authenticated_client):
    client = authenticated_client
    identity = create(client)
    db = app.state.database
    balance = db.club_finances.find_one({"_id": identity})["balance"]
    assert client.post("/api/stadium/evolve").status_code == 409
    assert db.club_finances.find_one({"_id": identity})["balance"] == balance
    assert db.stadiums.find_one({"_id": identity})["capacity"] == 10000
    assert client.post("/api/stadium/gym/upgrade").status_code == 409
    db.club_finances.update_one({"_id": identity}, {"$set": {"balance": 1_000_000_000}})
    for level, _, capacity, _, _ in STADIUM_LEVELS[1:]:
        response = client.post("/api/stadium/evolve")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["arena_level"] == level and data["capacity"] == capacity
        assert sum(s["capacity"] for s in data["sectors"]) == capacity
    assert client.post("/api/stadium/evolve").status_code == 409
    response = client.post("/api/stadium/skyboxes/upgrade")
    assert response.status_code == 200
    assert next(s["capacity"] for s in response.json()["sectors"] if s["id"] == "skybox") > 0


def test_facility_effects_and_matchday_income_use_sector_prices(authenticated_client):
    client = authenticated_client
    identity = create(client)
    db = app.state.database
    assert client.post("/api/stadium/medical/upgrade").status_code == 200
    assert client.post("/api/stadium/medical/upgrade").json()["facilities"]["medical"] == 3
    assert (
        client.put("/api/stadium/sectors/lower_north/price", json={"price": 5000}).status_code
        == 200
    )
    # Services can be verified without needing a complete season.
    db.stadiums.update_one(
        {"_id": identity}, {"$set": {"facilities.shops": 2, "facilities.museum": 1}}
    )
    match = db.matches.find_one({"home_club_id": identity})
    repo = GameRepository(db)
    repo.transaction(lambda tx: FanBaseService.after_match(tx, match, 2, 1))
    history = db.ticket_history.find_one({"match_id": match["_id"]})
    assert history["income"] == sum(row["attendance"] * row["price"] for row in history["sectors"])
    assert history["attendance"] == sum(row["attendance"] for row in history["sectors"])
    assert history["services_income"] > 0
    assert (
        db.financial_transactions.count_documents(
            {"club_id": identity, "category": "other_income", "reference_id": match["_id"]}
        )
        == 1
    )
