from bson import ObjectId
from test_competition import add_club

from app.config.game import GameConfig
from app.main import app
from app.models.game import utcnow
from app.repositories.game import GameRepository
from app.services.competition import CompetitionService, SeasonFinalizationService
from app.services.game import MarketService


def test_extinction_keeps_human_series_and_handles_both_loan_directions(client):
    _, human = add_club()
    db = app.state.database
    repo = GameRepository(db)
    human_id = ObjectId(human["id"])
    upper = db.divisions.find_one({"tier": 0})
    lower = repo.insert("divisions", {"_id": ObjectId(), "tier": 1, "name": "B", "active": True})
    bot = CompetitionService.create_bot(repo, 1, 0, GameConfig())
    bot_id = bot["_id"]
    outgoing = db.players.find_one({"owner_club_id": bot_id})
    incoming = db.players.find_one({"owner_club_id": human_id})
    human_contract = db.player_contracts.find_one({"player_id": incoming["_id"]})
    for player, borrower in ((outgoing, human_id), (incoming, bot_id)):
        db.players.update_one({"_id": player["_id"]}, {"$set": {"current_club_id": borrower}})
        db.player_loans.insert_one(
            {
                "player_id": player["_id"],
                "owner_club_id": player["owner_club_id"],
                "current_club_id": borrower,
                "status": "active",
            }
        )
        db.lineups.update_one({"_id": borrower}, {"$addToSet": {"reserves": player["_id"]}})
    listing = db.transfer_listings.insert_one(
        {"player_id": outgoing["_id"], "status": "active"}
    ).inserted_id
    offer = db.transfer_offers.insert_one({"listing_id": listing, "status": "pending"}).inserted_id
    destinations = {human_id: 0, bot_id: 1}
    remaining = repo.transaction(
        lambda transaction: SeasonFinalizationService.extinguish_bot_divisions(
            transaction, [upper, lower], destinations, utcnow()
        )
    )
    assert [division["tier"] for division in remaining] == [0]
    assert destinations == {human_id: 0}
    assert db.clubs.find_one({"_id": human_id}).get("active", True) is True
    assert db.clubs.find_one({"_id": bot_id})["active"] is False
    assert db.players.count_documents({"owner_club_id": bot_id}) == 0
    free = db.players.find_one({"_id": outgoing["_id"]})
    assert free["owner_club_id"] is None and free["current_club_id"] is None
    assert free["salary"] == 0 and free["status"] == "available"
    available = MarketService(repo).search({"status": "free_agent"})
    assert str(outgoing["_id"]) in {player["id"] for player in available}
    assert outgoing["_id"] not in db.lineups.find_one({"_id": human_id})["reserves"]
    returned = db.players.find_one({"_id": incoming["_id"]})
    assert returned["current_club_id"] == returned["owner_club_id"] == human_id
    assert db.player_contracts.find_one({"player_id": incoming["_id"]}) == human_contract
    assert db.player_loans.find_one({"player_id": incoming["_id"]})["status"] == "returned"
    assert db.player_loans.find_one({"player_id": outgoing["_id"]})["status"] == "terminated"
    assert db.transfer_listings.find_one({"_id": listing})["status"] == "closed"
    assert db.transfer_offers.find_one({"_id": offer})["status"] == "closed"


def test_bot_series_above_a_human_series_is_not_extinguished(client):
    _, human = add_club()
    db = app.state.database
    repo = GameRepository(db)
    upper = db.divisions.find_one({"tier": 0})
    lower = repo.insert("divisions", {"_id": ObjectId(), "tier": 1, "name": "B", "active": True})
    bot = db.clubs.find_one({"is_bot": True, "active": True})
    destinations = {bot["_id"]: 0, ObjectId(human["id"]): 1}
    remaining = repo.transaction(
        lambda transaction: SeasonFinalizationService.extinguish_bot_divisions(
            transaction, [upper, lower], destinations, utcnow()
        )
    )
    assert [division["tier"] for division in remaining] == [0, 1]
    assert db.clubs.find_one({"_id": bot["_id"]})["active"] is True
    assert db.divisions.count_documents({"active": False}) == 0
