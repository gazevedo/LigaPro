from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from bson import ObjectId

from app.main import app
from app.models.game import utcnow
from app.repositories.game import GameRepository
from app.services.game import process_due


def account(client, index):
    response = client.post(
        "/api/auth/register",
        json={
            "name": f"Manager {index}",
            "email": f"manager{index}@example.com",
            "password": "test-password-123",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def create(client, headers, name="Clube teste"):
    response = client.post(
        "/api/clubs", headers=headers, json={"name": name, "country_id": "BR", "badge_id": "blue"}
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def clubs(client):
    seller, buyer = account(client, 1), account(client, 2)
    first, second = create(client, seller), create(client, buyer, "Clube comprador")
    return seller, buyer, first, second


def reserve(client, headers):
    squad = client.get("/api/squad", headers=headers).json()
    return next(p for p in squad["players"] if p["id"] in squad["lineup"]["reserves"])


def listing_offer(client, clubs, kind="sale"):
    seller, buyer, _, _ = clubs
    player = reserve(client, seller)
    listing = client.post(
        "/api/market/listings",
        headers=seller,
        json={"player_id": player["id"], "type": kind, "price": 100000, "duration_days": 1},
    )
    assert listing.status_code == 201, listing.text
    offer = client.post(
        "/api/market/offers",
        headers=buyer,
        json={"listing_id": listing.json()["id"], "amount": 100000},
    )
    assert offer.status_code == 201, offer.text
    return player, listing.json(), offer.json()


def test_create_club_and_initial_data(client):
    headers = account(client, 1)
    assert client.get("/api/game/status", headers=headers).json() == {"club": None}
    catalog = client.get("/api/game/catalog", headers=headers).json()
    assert len(catalog["countries"]) == 249
    assert {"BR", "PT", "AR", "JP", "US"} <= {item["id"] for item in catalog["countries"]}
    assert len({item["id"] for item in catalog["countries"]}) == 249
    assert len(catalog["badges"]) == 8
    assert {"blue", "red", "green"} <= {item["id"] for item in catalog["badges"]}
    club = create(client, headers)
    assert client.get("/api/game/status", headers=headers).json()["club"]["id"] == club["id"]
    squad = client.get("/api/squad", headers=headers).json()
    assert len(squad["players"]) == 25
    assert len(squad["lineup"]["starters"]) == 11
    assert len(squad["lineup"]["reserves"]) == 14
    assert set(p["position"] for p in squad["players"]) == {"GK", "FB", "CB", "MID", "ATT"}
    assert client.get("/api/finance", headers=headers).json()["balance"] == 10000000
    assert len(client.get("/api/finance/sponsors", headers=headers).json()["contracts"]) == 1
    assert (
        client.post(
            "/api/clubs",
            headers=headers,
            json={"name": "Segundo clube", "country_id": "BR", "badge_id": "blue"},
        ).status_code
        == 409
    )
    assert app.state.database.clubs.count_documents({"is_bot": {"$ne": True}}) == 1
    assert app.state.database.clubs.count_documents({"is_bot": True}) == 19


def test_public_club_and_permissions(client, clubs):
    seller, buyer, first, second = clubs
    public = client.get(f"/api/clubs/{first['id']}", headers=buyer).json()
    assert public["name"] == first["name"]
    assert not {"owner_user_id", "balance", "finances"} & public.keys()
    assert client.get("/api/game/status").status_code == 401
    stranger = account(client, 3)
    for endpoint in [
        "/api/squad",
        "/api/stadium",
        "/api/finance",
        "/api/finance/bank",
        "/api/finance/tickets",
        "/api/finance/sponsors",
        "/api/calendar",
        "/api/market/mine",
    ]:
        assert client.get(endpoint, headers=stranger).status_code == 403
    client.post("/api/stadium/stands/upgrade", headers=buyer)
    assert (
        app.state.database.stadiums.find_one({"_id": ObjectId(first["id"])})["facilities"]["stands"]
        == 1
    )
    assert (
        app.state.database.stadiums.find_one({"_id": ObjectId(second["id"])})["facilities"][
            "stands"
        ]
        == 2
    )
    assert (
        client.put(
            "/api/settings/game_rules", headers=seller, json={"value": {"initial_balance": 999999}}
        ).status_code
        == 403
    )


def test_lineup_validation(client, clubs):
    seller, buyer, _, _ = clubs
    lineup = client.get("/api/squad", headers=seller).json()["lineup"]
    data = {key: lineup[key] for key in ["formation", "starters", "reserves"]}
    assert client.put("/api/squad/lineup", headers=seller, json=data).status_code == 200
    duplicate = {**data, "starters": [data["starters"][0]] * 11}
    assert client.put("/api/squad/lineup", headers=seller, json=duplicate).status_code == 422
    other = client.get("/api/squad", headers=buyer).json()["lineup"]
    assert (
        client.put(
            "/api/squad/lineup", headers=seller, json={key: other[key] for key in data}
        ).status_code
        == 422
    )
    wrong = {**data, "formation": "4-3-3"}
    assert client.put("/api/squad/lineup", headers=seller, json=wrong).status_code == 422
    assert (
        client.put(
            "/api/squad/lineup", headers=seller, json={**data, "starters": data["starters"][:10]}
        ).status_code
        == 422
    )


def test_stadium_upgrade_and_insufficient_balance(client, clubs):
    seller, _, first, _ = clubs
    before = client.get("/api/finance", headers=seller).json()["balance"]
    upgrade = client.post("/api/stadium/stands/upgrade", headers=seller)
    assert upgrade.status_code == 200, upgrade.text
    assert upgrade.json()["capacity"] == 11000
    assert client.get("/api/finance", headers=seller).json()["balance"] == before - 100000
    app.state.database.club_finances.update_one(
        {"_id": ObjectId(first["id"])}, {"$set": {"balance": 0}}
    )
    assert client.post("/api/stadium/pitch/upgrade", headers=seller).status_code == 409
    assert client.get("/api/stadium", headers=seller).json()["facilities"]["pitch"] == 1
    assert client.post("/api/stadium/unknown/upgrade", headers=seller).status_code == 404


def test_bank_tickets_sponsors_calendar(client, clubs):
    seller, buyer, first, _ = clubs
    investment = client.post(
        "/api/finance/bank/investment", headers=seller, json={"amount": 100000}
    )
    assert investment.status_code == 201, investment.text
    identity = investment.json()["id"]
    assert (
        client.post(f"/api/finance/contracts/{identity}/settle", headers=buyer).status_code == 403
    )
    assert (
        client.post(f"/api/finance/contracts/{identity}/settle", headers=seller).status_code == 409
    )
    assert (
        client.post(
            "/api/finance/bank/bank_loan", headers=seller, json={"amount": 100000}
        ).status_code
        == 409
    )
    app.state.database.bank_contracts.update_one(
        {"_id": ObjectId(identity)}, {"$set": {"ends_at": utcnow() - timedelta(seconds=1)}}
    )
    assert (
        client.post(f"/api/finance/contracts/{identity}/settle", headers=seller).status_code == 200
    )
    loan = client.post("/api/finance/bank/bank_loan", headers=seller, json={"amount": 100000})
    assert loan.status_code == 201
    assert (
        client.post(
            "/api/finance/bank/bank_loan", headers=seller, json={"amount": 100000}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/finance/contracts/{loan.json()['id']}/settle", headers=seller
        ).status_code
        == 200
    )
    assert (
        client.put("/api/finance/tickets", headers=seller, json={"price": 3500}).json()["price"]
        == 3500
    )
    assert client.get("/api/finance/tickets", headers=seller).json()["history"] == []
    assert client.get("/api/finance/tickets", headers=seller).json()["income"] == 0
    assert client.post("/api/finance/sponsors/principal/accept", headers=seller).status_code == 409
    app.state.database.sponsor_contracts.update_many(
        {"club_id": ObjectId(first["id"])}, {"$set": {"ends_at": utcnow() - timedelta(days=1)}}
    )
    assert client.post("/api/finance/sponsors/principal/accept", headers=seller).status_code == 200
    events = client.get("/api/calendar", headers=seller).json()
    assert events and sum(e["type"] == "match" for e in events) == 38
    assert len(client.get("/api/calendar?type=match", headers=seller).json()) == 38
    assert all(
        e["type"] == "financial"
        for e in client.get("/api/calendar?type=financial", headers=seller).json()
    )
    assert client.get("/api/calendar?start=2100-01-01T00:00:00Z", headers=seller).json() == []
    assert (
        client.get(
            "/api/calendar?start=2100-01-01T00:00:00Z&end=2000-01-01T00:00:00Z", headers=seller
        ).status_code
        == 422
    )


def test_atomic_sale_and_conflicting_offers(client, clubs):
    seller, buyer, first, second = clubs
    player, listing, offer = listing_offer(client, clubs)
    third = account(client, 3)
    create(client, third, "Terceiro clube")
    conflict = client.post(
        "/api/market/offers", headers=third, json={"listing_id": listing["id"], "amount": 110000}
    ).json()
    assert client.post(f"/api/market/offers/{offer['id']}/accept", headers=buyer).status_code == 403
    response = client.post(f"/api/market/offers/{offer['id']}/accept", headers=seller)
    assert response.status_code == 200, response.text
    assert (
        client.post(f"/api/market/negotiations/{offer['id']}/confirm", headers=buyer).status_code
        == 200
    )
    moved = client.get(f"/api/players/{player['id']}", headers=buyer).json()
    assert moved["owner_club_id"] == moved["current_club_id"] == second["id"]
    assert client.get("/api/finance", headers=seller).json()["balance"] == 10100000
    assert client.get("/api/finance", headers=buyer).json()["balance"] == 9900000
    assert app.state.database.transfer_history.count_documents({}) == 1
    assert (
        app.state.database.transfer_offers.find_one({"_id": ObjectId(conflict["id"])})["status"]
        == "closed"
    )
    assert (
        client.post(f"/api/market/offers/{offer['id']}/accept", headers=seller).status_code == 409
    )
    assert player["id"] not in client.get("/api/squad", headers=seller).json()["lineup"]["reserves"]
    assert player["id"] in client.get("/api/squad", headers=buyer).json()["lineup"]["reserves"]
    assert client.get("/api/market/players?type=sale", headers=seller).json() == []
    assert first["id"] != second["id"]


def test_sale_rolls_back_without_balance(client, clubs):
    seller, buyer, first, second = clubs
    player, _, offer = listing_offer(client, clubs)
    app.state.database.club_finances.update_one(
        {"_id": ObjectId(second["id"])}, {"$set": {"balance": 0}}
    )
    assert (
        client.post(f"/api/market/offers/{offer['id']}/accept", headers=seller).status_code == 200
    )
    assert (
        client.post(f"/api/market/negotiations/{offer['id']}/confirm", headers=buyer).status_code
        == 409
    )
    assert (
        client.get(f"/api/players/{player['id']}", headers=buyer).json()["owner_club_id"]
        == first["id"]
    )
    assert app.state.database.transfer_history.count_documents({}) == 0
    assert client.get("/api/finance", headers=seller).json()["balance"] == 10000000
    assert (
        app.state.database.transfer_offers.find_one({"_id": ObjectId(offer["id"])})["status"]
        == "player_accepted"
    )


def test_loan_returns_without_user_online(client, clubs):
    seller, buyer, first, second = clubs
    player, _, offer = listing_offer(client, clubs, "loan")
    assert (
        client.post(f"/api/market/offers/{offer['id']}/accept", headers=seller).status_code == 200
    )
    assert (
        client.post(f"/api/market/negotiations/{offer['id']}/confirm", headers=buyer).status_code
        == 200
    )
    moved = client.get(f"/api/players/{player['id']}", headers=buyer).json()
    assert moved["owner_club_id"] == first["id"] and moved["current_club_id"] == second["id"]
    app.state.database.player_loans.update_many(
        {}, {"$set": {"ends_at": utcnow() - timedelta(seconds=1)}}
    )
    process_due(GameRepository(app.state.database))
    process_due(GameRepository(app.state.database))
    returned = client.get(f"/api/players/{player['id']}", headers=buyer).json()
    assert returned["current_club_id"] == returned["owner_club_id"] == first["id"]
    assert app.state.database.player_loans.find_one({})["status"] == "returned"
    assert len(client.get("/api/squad", headers=buyer).json()["lineup"]["starters"]) == 11


def test_market_filters_cancel_and_ownership(client, clubs):
    seller, buyer, _, _ = clubs
    player, listing, offer = listing_offer(client, clubs)
    query = (
        f"/api/market/players?name={player['name']}&position={player['position']}"
        f"&age_min={player['age']}&age_max={player['age']}"
        f"&overall_min={player['overall']}&overall_max={player['overall']}"
        f"&value_min={player['value']}&value_max={player['value']}&country_id=BR&type=sale"
    )
    assert len(client.get(query, headers=buyer).json()) == 1
    assert client.get("/api/market/players?age_min=40", headers=buyer).json() == []
    assert (
        client.post(
            "/api/market/listings",
            headers=buyer,
            json={"player_id": player["id"], "type": "sale", "price": 100000},
        ).status_code
        == 403
    )
    assert (
        client.post(f"/api/market/listings/{listing['id']}/cancel", headers=buyer).status_code
        == 403
    )
    assert client.post(f"/api/market/offers/{offer['id']}/cancel", headers=buyer).status_code == 200
    assert (
        client.post(f"/api/market/listings/{listing['id']}/cancel", headers=seller).status_code
        == 200
    )


def test_concurrent_accept_does_not_double_charge(client, clubs):
    seller, buyer, _, _ = clubs
    _, _, offer = listing_offer(client, clubs)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: (
                    client.post(
                        f"/api/market/offers/{offer['id']}/accept", headers=seller
                    ).status_code
                ),
                range(2),
            )
        )
    assert sorted(results) == [200, 409]
    assert (
        client.post(f"/api/market/negotiations/{offer['id']}/confirm", headers=buyer).status_code
        == 200
    )
    assert client.get("/api/finance", headers=buyer).json()["balance"] == 9900000
    assert app.state.database.transfer_history.count_documents({}) == 1


def test_due_investment_is_idempotent(client, clubs):
    seller, _, _, _ = clubs
    response = client.post("/api/finance/bank/investment", headers=seller, json={"amount": 100000})
    app.state.database.bank_contracts.update_one(
        {"_id": ObjectId(response.json()["id"])},
        {"$set": {"ends_at": utcnow() - timedelta(seconds=1)}},
    )
    repo = GameRepository(app.state.database)
    process_due(repo)
    process_due(repo)
    assert client.get("/api/finance", headers=seller).json()["balance"] == 10001000
    assert (
        app.state.database.financial_transactions.count_documents({"category": "bank_settlement"})
        == 1
    )


def test_club_creation_failure_leaves_no_partial_documents(client):
    headers = account(client, 1)
    response = client.post(
        "/api/clubs",
        headers=headers,
        json={"name": "Clube teste", "country_id": "XX", "badge_id": "blue"},
    )
    assert response.status_code == 422
    for collection in ["clubs", "players", "stadiums", "lineups", "club_finances"]:
        assert app.state.database[collection].count_documents({}) == 0


def test_calendar_requires_timezone(client, clubs):
    seller, _, _, _ = clubs
    assert client.get("/api/calendar?start=2026-01-01T00:00:00", headers=seller).status_code == 422


def test_large_squad_is_not_truncated_and_can_save(client, clubs):
    seller, _, first, _ = clubs
    cid = ObjectId(first["id"])
    template = app.state.database.players.find_one({"current_club_id": cid})
    extras = [{**template, "_id": ObjectId(), "name": f"Reserva {index}"} for index in range(210)]
    app.state.database.players.insert_many(extras)
    app.state.database.lineups.update_one(
        {"_id": cid}, {"$push": {"reserves": {"$each": [p["_id"] for p in extras]}}}
    )
    squad = client.get("/api/squad", headers=seller).json()
    assert len(squad["players"]) == 235
    lineup = {key: squad["lineup"][key] for key in ["formation", "starters", "reserves"]}
    assert len(lineup["reserves"]) == 224
    assert client.put("/api/squad/lineup", headers=seller, json=lineup).status_code == 200


def test_player_details_use_identity_even_with_duplicate_names(client, clubs):
    seller, buyer, _, _ = clubs
    player, listing, _ = listing_offer(client, clubs)
    details = client.get(f"/api/players/{player['id']}", headers=buyer).json()
    assert details["listing"]["id"] == listing["id"]
    db = app.state.database
    second_player = db.players.find_one({"_id": {"$ne": ObjectId(player["id"])}})
    db.players.update_many(
        {"name": player["name"], "_id": {"$ne": ObjectId(player["id"])}},
        {"$set": {"name": "Outro nome"}},
    )
    db.players.update_one({"_id": second_player["_id"]}, {"$set": {"name": player["name"]}})
    same_name = client.get("/api/market/players?name=" + player["name"], headers=seller).json()
    assert len(same_name) == 2
    assert sum(p["listing"] is not None for p in same_name) == 1


def test_ticket_income_counts_all_transactions(client, clubs):
    seller, _, first, _ = clubs
    app.state.database.financial_transactions.insert_many(
        [
            {
                "club_id": ObjectId(first["id"]),
                "amount": 100,
                "category": "ticket_income",
                "created_at": utcnow(),
            }
            for _ in range(205)
        ]
    )
    assert client.get("/api/finance/tickets", headers=seller).json()["income"] == 20500


def test_create_club_with_expanded_catalog(client):
    headers = account(client, 99)
    response = client.post(
        "/api/clubs",
        headers=headers,
        json={"name": "Tokyo Stars", "country_id": "JP", "badge_id": "night"},
    )
    assert response.status_code == 201, response.text
    club = response.json()
    assert club["country"]["name"] == "Japão"
    assert club["badge"]["pattern"] == "cross"
    assert club["badge"]["accent"] == "#facc15"
    assert client.get("/api/game/status", headers=headers).json()["club"]["id"] == club["id"]


def test_market_sorts_results_before_limit(client):
    headers = account(client, 1)
    create(client, headers)
    for sort, field, reverse in [
        ("value_asc", "market_value", False),
        ("value_desc", "market_value", True),
        ("strength_desc", "strength", True),
        ("strength_asc", "strength", False),
    ]:
        response = client.get(f"/api/market/players?sort={sort}", headers=headers)
        assert response.status_code == 200
        values = [row[field] for row in response.json()]
        assert values == sorted(values, reverse=reverse)
    assert client.get("/api/market/players?sort=invalid", headers=headers).status_code == 422
