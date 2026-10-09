from datetime import timedelta
from random import Random

from bson import ObjectId
from test_game import account, create

from app.config.game import GameConfig
from app.main import app
from app.repositories.game import GameRepository
from app.services.career_development import CareerDevelopmentService
from app.services.competition import CompetitionService
from app.services.fan_base import FanBaseService
from app.services.monthly_finance import MonthlyFinanceService
from app.services.player_development import PlayerGeneratorService
from app.services.season_calendar import FriendlyService, SeasonCalendarService
from app.services.sponsorship import SponsorshipService


def setup(client):
    headers = account(client, 1)
    club = create(client, headers)
    repo = GameRepository(app.state.database)
    return headers, ObjectId(club["id"]), repo


def test_cpe_selection_promotion_and_bounded_generation(client):
    headers, club, repo = setup(client)
    rows = client.get("/api/youth", headers=headers).json()
    assert len(rows) == 3 and all(
        p["status"] == "candidate"
        and not p["can_train"]
        and 14 <= p["age"] <= 17
        and p["strength"] <= p["estimated_potential_capacity"] <= 100
        for p in rows
    )
    assert client.post(f"/api/players/{rows[0]['id']}/train", headers=headers).status_code == 409
    assert client.post(f"/api/youth/{rows[0]['id']}/promote", headers=headers).status_code == 409
    promoted = rows[0]
    assert client.post(f"/api/youth/{promoted['id']}/select", headers=headers).status_code == 200
    assert client.post(f"/api/youth/{rows[1]['id']}/select", headers=headers).status_code == 409
    assert len(client.get("/api/youth", headers=headers).json()) == 1
    repo.update("youth_players", {"_id": ObjectId(promoted["id"])}, {"$set": {"age": 18}})
    result = client.post(f"/api/youth/{promoted['id']}/promote", headers=headers)
    assert result.status_code == 200, result.text
    assert "estimated_potential_capacity" not in result.json() and "potential" not in result.json()
    assert repo.find(
        "player_contracts", {"player_id": ObjectId(promoted["id"]), "status": "active"}
    )
    assert not client.get("/api/youth", headers=headers).json()
    season = CompetitionService.current(repo)
    club_doc = repo.find("clubs", {"_id": club})
    # Existing academy players remain; the candidate trio is not counted as roster space.
    generator = PlayerGeneratorService(seed=100)
    repo.insert_many("youth_players", [generator.player(club, "BR", youth=True) for _ in range(20)])
    fake = {**season, "_id": ObjectId(), "number": season["number"] + 1}
    repo.update("seasons", {"_id": season["_id"]}, {"$set": {"status": "completed"}})
    repo.insert("seasons", fake)
    repo.transaction(lambda tx: CompetitionService.generate_youth(tx, club_doc, fake, GameConfig()))
    candidates = [
        p for p in client.get("/api/youth", headers=headers).json() if p["status"] == "candidate"
    ]
    assert len(candidates) == 3
    assert (
        client.post(f"/api/youth/{candidates[0]['id']}/select", headers=headers).status_code == 409
    )
    active = client.get("/api/youth", headers=headers).json()
    selected = next(p for p in active if p["status"] == "available")
    assert client.post(f"/api/youth/{selected['id']}/release", headers=headers).status_code == 200
    assert (
        client.post(f"/api/youth/{candidates[0]['id']}/select", headers=headers).status_code == 200
    )


def test_youth_choice_is_serialized_between_two_devices(client):
    from concurrent.futures import ThreadPoolExecutor

    headers, club, repo = setup(client)
    candidates = client.get("/api/youth", headers=headers).json()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda p: client.post(f"/api/youth/{p['id']}/select", headers=headers),
                candidates[:2],
            )
        )
    assert sorted(result.status_code for result in results) == [200, 409]
    assert (
        repo.database.youth_players.count_documents(
            {"current_club_id": club, "status": "available"}
        )
        == 1
    )


def test_youth_candidates_cannot_be_selected_by_another_club(client):
    headers, club, repo = setup(client)
    other_headers = account(client, 2)
    create(client, other_headers)
    candidate = client.get("/api/youth", headers=headers).json()[0]
    assert (
        client.post(f"/api/youth/{candidate['id']}/select", headers=other_headers).status_code
        == 403
    )


def test_ten_season_careers_are_bounded_and_retire_progressively(client):
    generator = PlayerGeneratorService(seed=27)
    young = [generator.player("club", "BR") for _ in range(400)]
    old = [generator.player("club", "BR") for _ in range(400)]
    for p in young:
        p["age"] = 17
    for p in old:
        p["age"] = 34
    initial = sum(p["strength"] for p in young) / len(young)
    retirees = []
    for season in range(10):
        rng = Random(season)
        retired = 0
        for cohort in [young, old]:
            for p in cohort:
                if p.get("retired"):
                    continue
                values, _ = CareerDevelopmentService.evolve(p, rng, 2000, 100)
                p.update(values)
                retired += int(values["retired"])
        retirees.append(retired)
    assert sum(p["strength"] for p in young) / len(young) > initial
    assert sum(p["strength"] for p in old) / len(old) < initial + 2
    assert sum(p["retired"] for p in old) > 150
    assert max(p["strength"] for p in young + old) < 80
    assert sum(retirees[5:]) > sum(retirees[:5])


def test_calendar_markers_idempotency_and_friendly_conflicts(client):
    headers, club, repo = setup(client)
    season = CompetitionService.current(repo)
    repo.transaction(lambda tx: SeasonCalendarService.ensure(tx, club, season))
    repo.transaction(lambda tx: SeasonCalendarService.ensure(tx, club, season))
    assert (
        repo.database.calendar_events.count_documents({"club_id": club, "type": "financial_close"})
        == 12
    )
    assert (
        repo.database.calendar_events.count_documents(
            {"club_id": club, "type": "transfer_window_open"}
        )
        == 2
    )
    rival = repo.find("clubs", {"is_bot": True, "active": True})
    date = season["starts_at"] + timedelta(days=1)
    response = client.post(
        "/api/calendar/friendlies",
        headers=headers,
        json={"opponent_club_id": str(rival["_id"]), "date": date.isoformat()},
    )
    assert response.status_code == 201, response.text
    assert (
        client.post(
            "/api/calendar/friendlies",
            headers=headers,
            json={"opponent_club_id": str(rival["_id"]), "date": date.isoformat()},
        ).status_code
        == 409
    )
    identity = ObjectId(response.json()["id"])
    FriendlyService(repo).play(identity, date)
    FriendlyService(repo).play(identity, date)
    assert repo.find("friendly_matches", {"_id": identity})["status"] == "completed"
    assert repo.database.standings.count_documents({"games": {"$gt": 0}}) == 0


def test_sponsor_exclusivity_expiry_and_monthly_payout(client):
    headers, club, repo = setup(client)
    finance = repo.find("club_finances", {"_id": club})
    start = finance["finance_started_at"]
    repo.update_many(
        "sponsor_contracts", {"club_id": club}, {"$set": {"ends_at": start, "status": "expired"}}
    )
    offers = client.get("/api/finance/sponsors", headers=headers).json()["offers"]
    assert len(offers) == 2
    result = client.post(f"/api/finance/sponsors/{offers[0]['id']}/accept", headers=headers)
    assert result.status_code == 200, result.text
    assert (
        client.post(f"/api/finance/sponsors/{offers[1]['id']}/accept", headers=headers).status_code
        == 409
    )
    end = finance["next_month_at"]
    MonthlyFinanceService.process_due(repo, end)
    amount = sum(
        row["amount"]
        for row in repo.many(
            "financial_transactions", {"club_id": club, "category": "sponsorship"}, limit=None
        )
    )
    assert abs(amount - offers[0]["monthly_value"]) < 100
    assert SponsorshipService.value(
        {"reputation": 90, "division_tier": 0, "supporters": 30000}
    ) > SponsorshipService.value({"reputation": 10, "division_tier": 4, "supporters": 1000})


def test_attendance_expansion_and_training_structure(client):
    headers, club, repo = setup(client)
    stadium = repo.find("stadiums", {"_id": club})
    doc = repo.find("clubs", {"_id": club})
    assert FanBaseService.attendance(doc, stadium, price=500) > FanBaseService.attendance(
        doc, stadium, price=8000
    )
    assert FanBaseService.attendance({**doc, "supporters": 1000000}, stadium) <= stadium["capacity"]
    assert client.post("/api/stadium/stands/upgrade", headers=headers).status_code == 200
    assert repo.find("stadiums", {"_id": club})["capacity"] == stadium["capacity"] + 1000
    junior = repo.find("youth_players", {"current_club_id": club})
    repo.update("stadiums", {"_id": club}, {"$set": {"facilities.training": 3}})
    result = client.post(f"/api/players/{junior['_id']}/train", headers=headers)
    assert result.json()["training_progress"] == 3
