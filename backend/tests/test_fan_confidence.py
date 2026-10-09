from datetime import timedelta

from bson import ObjectId
from test_competition import add_club

from app.main import app
from app.repositories.game import GameRepository
from app.services.fan_base import FanBaseService
from app.services.sponsorship import SponsorshipService


def test_confidence_reduces_attendance_and_new_sponsorship_quotes():
    club = {"supporters": 10000, "reputation": 10, "division_tier": 0}
    stadium = {"capacity": 50000, "ticket_price": 2000}
    attendances = [
        FanBaseService.attendance({**club, "fan_satisfaction": value}, stadium)
        for value in (0, 50, 100)
    ]
    offers = [
        SponsorshipService.value({**club, "fan_satisfaction": value}) for value in (0, 50, 100)
    ]
    assert attendances[0] < attendances[1] < attendances[2]
    assert offers[0] < offers[1] < offers[2]
    assert FanBaseService.confidence({}) == 50
    assert FanBaseService.confidence({"fan_satisfaction": -20}) == 0
    assert FanBaseService.confidence({"fan_satisfaction": 150}) == 100


def test_public_confidence_preserves_existing_score_and_club_ownership(client):
    _, club = add_club()
    db = app.state.database
    repo = GameRepository(db)
    identity = ObjectId(club["id"])
    before = db.clubs.find_one({"_id": identity})
    assert club["fan_confidence"] == 50
    repo.transaction(
        lambda tx: FanBaseService.change(tx, identity, "test", ObjectId(), satisfaction=-100)
    )
    after = db.clubs.find_one({"_id": identity})
    assert after["fan_satisfaction"] == 0
    assert after["owner_user_id"] == before["owner_user_id"]
    from app.services.game import ClubService

    assert ClubService(repo).club(str(identity))["fan_confidence"] == 0
    repo.transaction(
        lambda tx: FanBaseService.change(tx, identity, "test", ObjectId(), satisfaction=200)
    )
    assert ClubService(repo).club(str(identity))["fan_confidence"] == 100


def test_lower_confidence_lowers_future_offers_but_preserves_signed_contract(client):
    _, club = add_club()
    db = app.state.database
    repo = GameRepository(db)
    identity = ObjectId(club["id"])
    signed = db.sponsor_contracts.find_one({"club_id": identity})
    period = (signed["ends_at"] - signed["starts_at"]) / 12
    initial_payment = SponsorshipService.monthly_income(
        repo, identity, signed["starts_at"], signed["starts_at"] + period
    )
    now = signed["starts_at"]
    high = {**db.clubs.find_one({"_id": identity}), "fan_satisfaction": 100}
    first = SponsorshipService.offers(repo, high, now)
    # Quotes expire as usual; the new valuation then reflects the current confidence.
    later = first[0]["expires_at"] + timedelta(seconds=1)
    db.clubs.update_one({"_id": identity}, {"$set": {"fan_satisfaction": 0}})
    low = db.clubs.find_one({"_id": identity})
    second = SponsorshipService.offers(repo, low, later)
    assert all(new["monthly_value"] < old["monthly_value"] for new, old in zip(second, first))
    assert db.sponsor_contracts.find_one({"_id": signed["_id"]}) == signed
    assert (
        SponsorshipService.monthly_income(
            repo, identity, signed["starts_at"], signed["starts_at"] + period
        )
        == initial_payment
    )
