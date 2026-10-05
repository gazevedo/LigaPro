from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from bson import ObjectId
from test_game import account, create

from app.main import app
from app.models.game import utcnow
from app.repositories.game import GameRepository
from app.services.bot_manager import BotManagerService
from app.services.competition import CompetitionService
from app.services.negotiation import NegotiationService
from app.services.physical_condition import PhysicalConditionService
from app.services.player_contracts import ContractService
from app.services.salary import SalaryService


def pair(client):
    seller = account(client, 1)
    first = create(client, seller)
    buyer = account(client, 2)
    second = create(client, buyer, "Comprador")
    db = app.state.database
    reserve = db.lineups.find_one({"_id": ObjectId(first["id"])})["reserves"][0]
    player = db.players.find_one({"_id": reserve})
    return seller, buyer, first, second, player


def send(client, buyer, player, **changes):
    payload = dict(
        player_id=str(player["_id"]),
        offer_type="sale",
        transfer_value=100000,
        salary_offer=SalaryService.reference(player),
        contract_months=24,
        loan_months=2,
        salary_share=0.5,
    )
    response = client.post("/api/market/negotiations", headers=buyer, json={**payload, **changes})
    assert response.status_code == 201, response.text
    return response.json()


def act(client, headers, offer, action):
    return client.post(f"/api/market/negotiations/{offer['id']}/{action}", headers=headers)


def test_staged_sale_and_concurrent_confirmation_are_atomic(client):
    seller, buyer, first, second, player = pair(client)
    db = app.state.database
    offer = send(client, buyer, player)
    cash = db.club_finances.find_one({"_id": ObjectId(second["id"])})["balance"]
    assert act(client, seller, offer, "confirm").status_code == 403
    assert act(client, buyer, offer, "confirm").status_code == 409
    assert act(client, seller, offer, "accept").json()["status"] == "player_accepted"
    assert db.players.find_one({"_id": player["_id"]})["owner_club_id"] == ObjectId(first["id"])
    assert db.club_finances.find_one({"_id": ObjectId(second["id"])})["balance"] == cash
    with ThreadPoolExecutor(2) as executor:
        statuses = list(
            executor.map(lambda _: act(client, buyer, offer, "confirm").status_code, range(2))
        )
    assert sorted(statuses) == [200, 409]
    assert db.players.find_one({"_id": player["_id"]})["owner_club_id"] == ObjectId(second["id"])
    assert (
        db.club_finances.find_one({"_id": ObjectId(second["id"])})["balance"]
        == cash - offer["amount"]
    )
    assert db.transfer_history.count_documents({"player_id": player["_id"]}) == 1
    assert (
        ContractService.current(GameRepository(db), player["_id"])["salary"]
        == offer["salary_offer"]
    )


def test_counter_player_rejection_and_cancellation(client):
    seller, buyer, _, _, player = pair(client)
    offer = send(client, buyer, player, salary_offer=1)
    response = act(client, seller, offer, "accept")
    assert response.json()["status"] == "player_rejected"
    assert act(client, buyer, offer, "confirm").status_code == 409
    offer = send(client, buyer, player)
    response = client.post(
        f"/api/market/negotiations/{offer['id']}/counter",
        headers=seller,
        json={"transfer_value": 200000},
    )
    assert response.json()["status"] == "counter_offer"
    assert act(client, buyer, offer, "accept_counter").json()["status"] == "player_accepted"
    assert client.post(f"/api/market/offers/{offer['id']}/cancel", headers=buyer).status_code == 200
    assert act(client, buyer, offer, "confirm").status_code == 409


def test_closed_window_expiration_and_confirmation_rechecks_cash(client):
    seller, buyer, _, second, player = pair(client)
    db = app.state.database
    offer = send(client, buyer, player)
    assert act(client, seller, offer, "accept").status_code == 200
    balance = db.club_finances.find_one({"_id": ObjectId(second["id"])})["balance"]
    db.club_finances.update_one({"_id": ObjectId(second["id"])}, {"$set": {"balance": 0}})
    assert act(client, buyer, offer, "confirm").status_code == 409
    db.club_finances.update_one({"_id": ObjectId(second["id"])}, {"$set": {"balance": balance}})
    repo = GameRepository(db)
    season = CompetitionService.current(repo)
    middle = season["starts_at"] + timedelta(days=10)
    # A future logical time closes the transfer window independently of wall-clock time.
    buyer_doc = db.clubs.find_one({"_id": ObjectId(second["id"])})
    db.transfer_offers.update_one(
        {"_id": ObjectId(offer["id"])}, {"$set": {"expires_at": middle + timedelta(days=1)}}
    )
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        repo.transaction(
            lambda tx: NegotiationService.approve_for_club(
                tx, buyer_doc, offer["id"], "confirm", now=middle
            )
        )
    assert exc.value.status_code == 409
    NegotiationService.expire(repo, middle + timedelta(days=2))
    assert db.transfer_offers.find_one({"_id": ObjectId(offer["id"])})["status"] == "expired"


def test_loan_salary_shares_and_automatic_return(client):
    seller, buyer, first, second, player = pair(client)
    db = app.state.database
    repo = GameRepository(db)
    contract = ContractService.current(repo, player["_id"])
    period = timedelta(seconds=contract["salary_period_seconds"])
    offer = send(client, buyer, player, offer_type="loan")
    assert offer["salary_offer"] == contract["salary"]
    assert (
        client.post(
            f"/api/market/negotiations/{offer['id']}/counter",
            headers=seller,
            json={"transfer_value": 100000, "salary_offer": contract["salary"] + 1},
        ).status_code
        == 422
    )
    assert act(client, seller, offer, "accept").status_code == 200
    assert act(client, buyer, offer, "confirm").status_code == 200
    loan = db.player_loans.find_one({"player_id": player["_id"], "status": "active"})
    assert loan["owner_club_id"] == ObjectId(first["id"])
    assert loan["current_club_id"] == ObjectId(second["id"])
    current = ContractService.current(repo, player["_id"])
    before = {
        club: db.club_finances.find_one({"_id": club})["balance"]
        for club in [loan["owner_club_id"], loan["current_club_id"]]
    }
    end = current["paid_until"] + period
    repo.transaction(
        lambda tx: ContractService.settle_salary(
            tx, ContractService.current(tx, player["_id"]), end
        )
    )
    costs = {
        club: before[club] - db.club_finances.find_one({"_id": club})["balance"] for club in before
    }
    assert sum(costs.values()) == contract["salary"]
    assert abs(costs[loan["current_club_id"]] - contract["salary"] * 0.5) <= 1
    repo.transaction(
        lambda tx: ContractService.settle_salary(
            tx, ContractService.current(tx, player["_id"]), end
        )
    )
    assert (
        db.club_finances.find_one({"_id": loan["current_club_id"]})["balance"]
        == before[loan["current_club_id"]] - costs[loan["current_club_id"]]
    )
    from app.services.game import MarketService

    MarketService.return_loans(repo, loan["ends_at"])
    assert db.players.find_one({"_id": player["_id"]})["current_club_id"] == loan["owner_club_id"]
    assert db.player_loans.find_one({"_id": loan["_id"]})["status"] == "returned"


def test_injury_blocks_lineup_and_training_and_recovers(client):
    headers = account(client, 1)
    club = create(client, headers)
    db = app.state.database
    squad = client.get("/api/squad", headers=headers).json()
    player_id = ObjectId(squad["lineup"]["starters"][1])
    end = utcnow() + timedelta(days=1)
    db.players.update_one(
        {"_id": player_id},
        {"$set": {"status": "injured", "injury_return_at": end, "physical_condition": 40}},
    )
    assert client.post(f"/api/players/{player_id}/train", headers=headers).status_code == 409
    assert client.put("/api/squad/lineup", headers=headers, json=squad["lineup"]).status_code == 422
    repo = GameRepository(db)
    repo.transaction(lambda tx: PhysicalConditionService().prepare(tx, ObjectId(club["id"]), end))
    assert db.players.find_one({"_id": player_id})["status"] == "available"
    assert db.players.find_one({"_id": player_id})["physical_condition"] > 40


def test_bot_management_is_budgeted_audited_and_idempotent(client):
    seller, _, first, _, _ = pair(client)
    db = app.state.database
    repo = GameRepository(db)
    bot = db.clubs.find_one({"is_bot": True, "active": True})
    # Seed one legal deficiency and a free replacement without injecting cash.
    reserve = db.players.find_one({"current_club_id": bot["_id"], "position": "GK"})
    db.players.update_one(
        {"_id": reserve["_id"]}, {"$set": {"current_club_id": None, "owner_club_id": None}}
    )
    ContractService.terminate(repo, reserve["_id"])
    now = utcnow()
    BotManagerService(repo).process_due(now)
    assert db.players.find_one({"_id": reserve["_id"]})["owner_club_id"] == bot["_id"]
    assert (
        db.bot_decisions.count_documents({"club_id": bot["_id"], "decision_type": "free_agent"})
        == 1
    )
    count = db.bot_decisions.count_documents({})
    BotManagerService(repo).process_due(now)
    assert db.bot_decisions.count_documents({}) == count
    assert db.club_finances.find_one({"_id": bot["_id"]})["balance"] >= 0
    assert not db.bot_decisions.find_one({"club_id": ObjectId(first["id"])})


def test_bots_buy_sell_renew_and_promote_using_shared_services(client):
    headers = account(client, 1)
    create(client, headers)
    db = app.state.database
    repo = GameRepository(db)
    bots = list(db.clubs.find({"is_bot": True, "active": True}).limit(2))
    seller, buyer = bots
    seller_lineup = db.lineups.find_one({"_id": seller["_id"]})
    outgoing = db.players.find_one({"_id": {"$in": seller_lineup["reserves"]}, "position": "GK"})
    buyer_lineup = db.lineups.find_one({"_id": buyer["_id"]})
    missing = db.players.find_one({"_id": {"$in": buyer_lineup["reserves"]}, "position": "GK"})
    ContractService.terminate(repo, missing["_id"])
    db.players.update_one({"_id": missing["_id"]}, {"$set": {"status": "retired"}})
    from app.schemas.game import ListingInput
    from app.services.bot_manager import BotContractService, BotTransferService, BotYouthService
    from app.services.game import MarketService

    now = utcnow()
    repo.transaction(
        lambda tx: MarketService.list_for_club(
            tx,
            seller,
            ListingInput(
                player_id=str(outgoing["_id"]), type="sale", price=1000000, duration_days=5
            ),
        )
    )
    repo.transaction(lambda tx: BotTransferService.manage(tx, buyer, now))
    offer = db.transfer_offers.find_one(
        {"buyer_club_id": buyer["_id"], "player_id": outgoing["_id"]}
    )
    assert offer is not None
    repo.transaction(lambda tx: BotTransferService.manage(tx, seller, now))
    assert db.transfer_offers.find_one({"_id": offer["_id"]})["status"] in {
        "counter_offer",
        "player_accepted",
    }
    repo.transaction(lambda tx: BotTransferService.manage(tx, buyer, now))
    assert db.players.find_one({"_id": outgoing["_id"]})["owner_club_id"] == buyer["_id"]
    assert db.transfer_history.find_one(
        {"seller_club_id": seller["_id"], "buyer_club_id": buyer["_id"]}
    )
    contract = ContractService.current(repo, outgoing["_id"])
    db.player_contracts.update_one(
        {"_id": contract["_id"]}, {"$set": {"expiring_at": now - timedelta(seconds=1)}}
    )
    repo.transaction(lambda tx: BotContractService.manage(tx, buyer, now))
    assert db.contract_history.find_one({"player_id": outgoing["_id"], "action": "renewed"})
    youth = db.youth_players.find_one({"current_club_id": seller["_id"]})
    db.youth_players.update_one(
        {"_id": youth["_id"]}, {"$set": {"age": 18, "strength": 65, "overall": 65}}
    )
    repo.transaction(lambda tx: BotYouthService.manage(tx, seller, now))
    assert db.players.find_one({"_id": youth["_id"]})
    assert db.bot_decisions.find_one({"player_id": youth["_id"]}) is None
    assert db.bot_decisions.find_one({"club_id": seller["_id"], "decision_type": "youth_promotion"})
