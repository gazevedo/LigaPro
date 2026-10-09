from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from bson import ObjectId
from test_game import account, create

from app.main import app
from app.models.game import utcnow
from app.repositories.game import GameRepository
from app.services.player_contracts import ContractService


def setup(client):
    headers = account(client, 1)
    club = create(client, headers)
    db = app.state.database
    player = db.players.find_one({"owner_club_id": ObjectId(club["id"])})
    contract = db.player_contracts.find_one({"player_id": player["_id"]})
    return headers, club, player, contract


def backdate(contract, months, expire=False):
    now = utcnow()
    period = timedelta(seconds=contract["salary_period_seconds"])
    started = now - months * period - timedelta(seconds=1)
    expires = now - timedelta(seconds=1) if expire else started + 24 * period
    app.state.database.player_contracts.update_one(
        {"_id": contract["_id"]},
        {
            "$set": {
                "started_at": started,
                "paid_until": started,
                "next_salary_at": started + period,
                "expires_at": expires,
                "expiring_at": expires - period,
            }
        },
    )
    return now, period


def test_creation_financial_view_and_youth_contract(client):
    headers, club, player, contract = setup(client)
    db = app.state.database
    contracts = list(
        db.player_contracts.find({"club_id": ObjectId(club["id"]), "status": "active"})
    )
    assert len(contracts) == 25
    assert db.player_contracts.count_documents({"status": "active"}) == db.players.count_documents(
        {}
    )
    assert contract["expires_at"] - contract["started_at"] == timedelta(days=60)
    assert contract["salary"] > 0
    finance = client.get("/api/finance", headers=headers).json()
    assert finance["monthly_payroll"] == sum(c["salary"] for c in contracts)
    assert len(finance["salary_costs"]) == 25
    assert finance["salary_history"] == []
    assert finance["total_contract_cost"] > finance["monthly_payroll"]
    youth = db.youth_players.find_one({"owner_club_id": ObjectId(club["id"])})
    assert client.post(f"/api/youth/{youth['_id']}/select", headers=headers).status_code == 200
    assert not db.player_contracts.find_one({"player_id": youth["_id"]})
    db.youth_players.update_one({"_id": youth["_id"]}, {"$set": {"age": 18}})
    assert client.post(f"/api/youth/{youth['_id']}/promote", headers=headers).status_code == 200
    assert db.player_contracts.find_one({"player_id": youth["_id"], "status": "active"})


def test_renewal_validates_ownership_salary_duration_balance_and_preserves_history(client):
    headers, club, player, contract = setup(client)
    url = f"/api/players/{player['_id']}/contract/renew"
    for data in (
        {"salary": 0, "seasons": 2},
        {"salary": True, "seasons": 2},
        {"salary": 5000, "seasons": 0},
        {"salary": 5000, "seasons": 6},
    ):
        assert client.post(url, headers=headers, json=data).status_code == 422
    foreign = account(client, 2)
    create(client, foreign, "Segundo clube")
    assert client.post(url, headers=foreign, json={"salary": 5000, "seasons": 2}).status_code == 403
    assert client.get(f"/api/players/{player['_id']}/contract", headers=foreign).status_code == 403
    before = client.get("/api/finance", headers=headers).json()
    assert (
        client.post(
            url, headers=headers, json={"salary": before["balance"], "seasons": 2}
        ).status_code
        == 409
    )
    assert (
        app.state.database.player_contracts.find_one({"_id": contract["_id"]})["status"] == "active"
    )
    response = client.post(url, headers=headers, json={"salary": 9000, "seasons": 3})
    assert response.status_code == 200, response.text
    new = response.json()
    assert new["salary"] == 9000 and new["id"] != str(contract["_id"])
    old = app.state.database.player_contracts.find_one({"_id": contract["_id"]})
    assert old["status"] == "terminated"
    assert old["expires_at"] == contract["expires_at"]
    current = client.get(f"/api/players/{player['_id']}/contract", headers=headers).json()
    assert current["contract"]["id"] == new["id"]
    assert {"created", "terminated", "renewed"} <= {e["action"] for e in current["history"]}
    assert (
        client.get("/api/finance", headers=headers).json()["monthly_payroll"]
        == before["monthly_payroll"] - contract["salary"] + 9000
    )


def test_salary_catches_up_offline_once_and_records_history(client):
    headers, club, player, contract = setup(client)
    now, period = backdate(contract, 3)
    db = app.state.database
    before = db.club_finances.find_one({"_id": ObjectId(club["id"])})["balance"]
    service = ContractService(GameRepository(db))
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: service.process_due(now), range(2)))
    service.process_due(now)
    assert (
        db.club_finances.find_one({"_id": ObjectId(club["id"])})["balance"]
        == before - 3 * contract["salary"]
    )
    assert (
        db.contract_history.count_documents(
            {"contract_id": contract["_id"], "action": "salary_paid"}
        )
        == 3
    )
    finance = client.get("/api/finance", headers=headers).json()
    assert len(finance["salary_history"]) == 3
    assert sum(t["amount"] for t in finance["salary_history"]) == -3 * contract["salary"]
    paid = db.player_contracts.find_one({"_id": contract["_id"]})
    assert paid["next_salary_at"] == paid["paid_until"] + period


def test_expiring_then_expired_free_agent_and_idempotence(client):
    headers, club, player, contract = setup(client)
    now, period = backdate(contract, 23)
    service = ContractService(GameRepository(app.state.database))
    service.process_due(now)
    stored = app.state.database.player_contracts.find_one({"_id": contract["_id"]})
    assert stored["status"] == "expiring"
    expires = stored["expires_at"]
    service.process_due(expires)
    service.process_due(expires + period)
    db = app.state.database
    assert db.player_contracts.find_one({"_id": contract["_id"]})["status"] == "expired"
    free = db.players.find_one({"_id": player["_id"]})
    assert free["status"] == "available"
    assert free["owner_club_id"] is None and free["current_club_id"] is None
    lineup = db.lineups.find_one({"_id": ObjectId(club["id"])})
    assert player["_id"] not in lineup["starters"] + lineup["reserves"]
    assert (
        db.contract_history.count_documents({"contract_id": contract["_id"], "action": "expired"})
        == 1
    )
    response = client.get("/api/market/players?status=free_agent", headers=headers)
    assert response.status_code == 200
    assert str(player["_id"]) in {p["id"] for p in response.json()}
    assert all(p["status"] == "available" for p in response.json())
    assert (
        client.post(
            f"/api/players/{player['_id']}/contract/renew",
            headers=headers,
            json={"salary": 5000, "seasons": 1},
        ).status_code
        == 403
    )


def test_free_agent_signing_is_atomic_and_adds_salary(client):
    headers, club, player, contract = setup(client)
    now, _ = backdate(contract, 12, expire=True)
    ContractService(GameRepository(app.state.database)).process_due(now)
    second = account(client, 2)
    second_club = create(client, second, "Segundo clube")
    before = client.get("/api/finance", headers=second).json()
    response = client.post(
        f"/api/market/players/{player['_id']}/sign",
        headers=second,
        json={"salary": 50000, "seasons": 2},
    )
    assert response.status_code == 201, response.text
    assert (
        client.post(
            f"/api/market/players/{player['_id']}/sign",
            headers=headers,
            json={"salary": 50000, "seasons": 2},
        ).status_code
        == 409
    )
    db = app.state.database
    acquired = db.players.find_one({"_id": player["_id"]})
    assert acquired["owner_club_id"] == ObjectId(second_club["id"])
    assert acquired["status"] == "available"
    assert player["_id"] in db.lineups.find_one({"_id": ObjectId(second_club["id"])})["reserves"]
    assert (
        client.get("/api/finance", headers=second).json()["monthly_payroll"]
        == before["monthly_payroll"] + 50000
    )
    assert db.player_contracts.count_documents({"player_id": player["_id"]}) == 2


def test_salary_obligations_do_not_block_expiration_when_balance_is_low(client):
    headers, club, player, contract = setup(client)
    now, _ = backdate(contract, 12, expire=True)
    db = app.state.database
    db.club_finances.update_one({"_id": ObjectId(club["id"])}, {"$set": {"balance": 0}})
    ContractService(GameRepository(db)).process_due(now)
    assert (
        db.club_finances.find_one({"_id": ObjectId(club["id"])})["balance"]
        == -12 * contract["salary"]
    )
    assert db.players.find_one({"_id": player["_id"]})["status"] == "available"
    assert (
        client.post(
            f"/api/market/players/{player['_id']}/sign",
            headers=headers,
            json={"salary": 5000, "seasons": 1},
        ).status_code
        == 409
    )


def test_expiration_closes_pending_market_and_active_loan(client):
    headers, club, player, contract = setup(client)
    db = app.state.database
    second = account(client, 2)
    borrowing = create(client, second, "Clube de empréstimo")
    borrower_id = ObjectId(borrowing["id"])
    # An active loan must not restore the old owner's link after expiry.
    db.players.update_one({"_id": player["_id"]}, {"$set": {"current_club_id": borrower_id}})
    db.lineups.update_one(
        {"_id": ObjectId(club["id"])},
        {"$pull": {"starters": player["_id"], "reserves": player["_id"]}},
    )
    db.lineups.update_one({"_id": borrower_id}, {"$addToSet": {"reserves": player["_id"]}})
    loan_id, listing_id, offer_id = ObjectId(), ObjectId(), ObjectId()
    db.player_loans.insert_one(
        {
            "_id": loan_id,
            "player_id": player["_id"],
            "owner_club_id": ObjectId(club["id"]),
            "current_club_id": borrower_id,
            "ends_at": utcnow() + timedelta(days=20),
            "status": "active",
        }
    )
    db.transfer_listings.insert_one(
        {"_id": listing_id, "player_id": player["_id"], "status": "active"}
    )
    db.transfer_offers.insert_one({"_id": offer_id, "listing_id": listing_id, "status": "pending"})
    now, _ = backdate(contract, 12, expire=True)
    ContractService(GameRepository(db)).process_due(now)
    assert db.player_loans.find_one({"_id": loan_id})["status"] == "expired"
    assert db.transfer_listings.find_one({"_id": listing_id})["status"] == "closed"
    assert db.transfer_offers.find_one({"_id": offer_id})["status"] == "closed"
    assert db.players.find_one({"_id": player["_id"]})["current_club_id"] is None
    assert player["_id"] not in db.lineups.find_one({"_id": borrower_id})["reserves"]


def test_concurrent_free_agent_signing_has_one_owner(client):
    first, club, player, contract = setup(client)
    second = account(client, 2)
    create(client, second, "Segundo clube")
    now, _ = backdate(contract, 12, expire=True)
    ContractService(GameRepository(app.state.database)).process_due(now)

    def sign(headers):
        return client.post(
            f"/api/market/players/{player['_id']}/sign",
            headers=headers,
            json={"salary": 50000, "seasons": 2},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(sign, (first, second)))
    assert sorted(statuses) == [201, 409]
    assert (
        app.state.database.player_contracts.count_documents(
            {"player_id": player["_id"], "status": "active"}
        )
        == 1
    )


def test_bootstrap_legacy_contracts_is_idempotent(client):
    headers, club, player, contract = setup(client)
    db = app.state.database
    db.player_contracts.delete_one({"_id": contract["_id"]})
    db.contract_history.delete_many({"contract_id": contract["_id"]})
    service = ContractService(GameRepository(db))
    service.bootstrap()
    service.bootstrap()
    assert db.player_contracts.count_documents({"player_id": player["_id"]}) == 1
    assert (
        db.contract_history.count_documents({"player_id": player["_id"], "action": "created"}) == 1
    )


def test_sale_moves_contract_while_loan_keeps_owner_payroll(client):
    headers, club, player, _ = setup(client)
    db = app.state.database
    second = account(client, 2)
    buyer = create(client, second, "Clube comprador")
    reserves = db.lineups.find_one({"_id": ObjectId(club["id"])})["reserves"]
    initial_buyer = client.get("/api/finance", headers=second).json()["monthly_payroll"]
    initial_owner = client.get("/api/finance", headers=headers).json()["monthly_payroll"]
    for kind, identity in zip(("sale", "loan"), reserves[:2]):
        original = db.player_contracts.find_one({"player_id": identity, "status": "active"})
        listing = client.post(
            "/api/market/listings",
            headers=headers,
            json={"player_id": str(identity), "type": kind, "price": 10000},
        ).json()
        offer = client.post(
            "/api/market/offers",
            headers=second,
            json={"listing_id": listing["id"], "amount": 10000},
        ).json()
        response = client.post(f"/api/market/offers/{offer['id']}/accept", headers=headers)
        assert response.status_code == 200, response.text
        assert (
            client.post(
                f"/api/market/negotiations/{offer['id']}/confirm", headers=second
            ).status_code
            == 200
        )
        contract = db.player_contracts.find_one({"player_id": identity, "status": "active"})
        assert contract["expires_at"] == original["expires_at"]
        if kind == "sale":
            assert contract["club_id"] == ObjectId(buyer["id"])
            assert db.player_contracts.find_one({"_id": original["_id"]})["status"] == "terminated"
            initial_buyer += original["salary"]
            initial_owner -= original["salary"]
        else:
            assert contract["_id"] == original["_id"]
            assert contract["club_id"] == ObjectId(club["id"])
        assert client.get("/api/finance", headers=second).json()["monthly_payroll"] == initial_buyer
        assert (
            client.get("/api/finance", headers=headers).json()["monthly_payroll"] == initial_owner
        )


def test_retirement_terminates_contract_and_stops_salary(client):
    from app.config.game import GameConfig
    from app.services.player_development import PlayerAgingService

    headers, club, player, contract = setup(client)
    db = app.state.database
    db.players.update_one({"_id": player["_id"]}, {"$set": {"age": 34}})
    config = GameConfig(RETIREMENT_PROBABILITIES=((35, 1),))
    repo = GameRepository(db)
    repo.transaction(lambda active: PlayerAgingService().process(active, ObjectId(), config))
    assert db.players.find_one({"_id": player["_id"]})["status"] == "retired"
    assert db.player_contracts.find_one({"_id": contract["_id"]})["status"] == "terminated"
    assert (
        db.contract_history.find_one({"contract_id": contract["_id"], "action": "terminated"})[
            "reason"
        ]
        == "retired"
    )
    assert client.get("/api/finance", headers=headers).json()["monthly_payroll"] == sum(
        c["salary"]
        for c in db.player_contracts.find({"club_id": ObjectId(club["id"]), "status": "active"})
    )
