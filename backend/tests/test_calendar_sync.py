from datetime import timedelta

from bson import ObjectId

from app.main import app
from app.models.game import utcnow
from app.models.player import SHIRT_NUMBERS
from app.repositories.game import GameRepository
from app.services.competition import CompetitionService
from app.services.game import SquadService


def club(client):
    response = client.post(
        "/api/clubs", json={"name": "Clube Sincronia", "country_id": "BR", "badge_id": "blue"}
    )
    assert response.status_code == 201, response.text
    return ObjectId(response.json()["id"])


def test_calendar_uses_same_fixtures_without_copied_events(authenticated_client):
    client = authenticated_client
    identity = club(client)
    db = app.state.database
    slot = db.season_clubs.find_one({"club_id": identity})
    query = {"$or": [{"home_slot_id": slot["_id"]}, {"away_slot_id": slot["_id"]}]}
    fixtures = list(db.matches.find(query).sort("round", 1))
    db.calendar_events.delete_many({"club_id": identity, "type": "match"})
    events = client.get("/api/calendar?type=league_match").json()
    assert len(events) == 38
    assert {event["reference_id"]: event["date"] for event in events} == {
        str(match["_id"]): match["date"].isoformat().replace("+00:00", "Z") for match in fixtures
    }
    assert len({event["id"] for event in events}) == 38
    old = fixtures[0]
    new_date = utcnow() + timedelta(days=4)
    db.matches.update_one({"_id": old["_id"]}, {"$set": {"date": new_date, "status": "live"}})
    # A stale copy must neither hide the fixture nor generate duplicates.
    for _ in range(2):
        db.calendar_events.insert_one(
            {
                "club_id": identity,
                "type": "match",
                "reference_id": old["_id"],
                "date": old["date"],
                "status": "scheduled",
                "title": "Desatualizada",
            }
        )
    result = client.get(
        "/api/calendar",
        params={
            "start": (new_date - timedelta(seconds=1)).isoformat(),
            "end": (new_date + timedelta(seconds=1)).isoformat(),
        },
    ).json()
    selected = [event for event in result if event.get("reference_id") == str(old["_id"])]
    assert len(selected) == 1 and selected[0]["status"] == "live"
    assert selected[0]["date"] != old["date"].isoformat().replace("+00:00", "Z")
    outside = client.get(
        "/api/calendar",
        params={
            "type": "league_match",
            "start": (old["date"] - timedelta(seconds=1)).isoformat(),
            "end": (old["date"] + timedelta(seconds=1)).isoformat(),
        },
    ).json()
    assert str(old["_id"]) not in {event.get("reference_id") for event in outside}


def test_calendar_preserves_inherited_slot_results_and_non_match_events(authenticated_client):
    client = authenticated_client
    identity = club(client)
    db = app.state.database
    slot = db.season_clubs.find_one({"club_id": identity})
    old = db.matches.find_one({"home_slot_id": slot["_id"]})
    prior_bot = db.clubs.find_one({"is_bot": True})["_id"]
    db.matches.update_one(
        {"_id": old["_id"]},
        {
            "$set": {
                "home_club_id": prior_bot,
                "status": "completed",
                "home_goals": 3,
                "away_goals": 2,
            }
        },
    )
    repo = GameRepository(db)
    owner = db.clubs.find_one({"_id": identity})["owner_user_id"]
    from types import SimpleNamespace

    official = CompetitionService(repo).matches(SimpleNamespace(id=str(owner)))
    calendar = client.get("/api/calendar?type=league_match").json()
    assert {event["reference_id"]: event["date"] for event in calendar} == {
        match["id"]: match["date"] for match in official
    }
    event = next(e for e in calendar if e["reference_id"] == str(old["_id"]))
    assert event["status"] == "completed" and event["home_goals"] == 3
    assert client.get("/api/calendar?type=season_start").json()


def test_existing_squad_position_migration_and_custom_number_are_idempotent(authenticated_client):
    client = authenticated_client
    identity = club(client)
    db = app.state.database
    db.players.update_many(
        {"current_club_id": identity},
        {
            "$set": {"shirt_number": 99},
            "$unset": {"shirt_number_revision": "", "shirt_number_custom": ""},
        },
    )
    migrated = client.get("/api/squad").json()["players"]
    assert len({p["shirt_number"] for p in migrated}) == 25
    assert all(p["shirt_number"] in SHIRT_NUMBERS[p["position"]] for p in migrated)
    target = migrated[0]
    assert (
        client.put(
            f"/api/squad/players/{target['id']}/shirt-number", json={"number": 99}
        ).status_code
        == 200
    )
    owner = db.clubs.find_one({"_id": identity})["owner_user_id"]
    from types import SimpleNamespace

    repo = GameRepository(db)
    repo.transaction(
        lambda tx: SquadService.ensure_shirt_numbers(tx, SimpleNamespace(id=str(owner)))
    )
    current = client.get("/api/squad").json()["players"]
    assert next(p["shirt_number"] for p in current if p["id"] == target["id"]) == 99
    assert all("shirt_number_revision" not in p and "shirt_number_custom" not in p for p in current)
