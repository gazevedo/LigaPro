from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException
from test_game import account, create

from app.main import app
from app.repositories.game import GameRepository
from app.schemas.game import ClubInput
from app.services.competition import CompetitionService, SeasonFinalizationService
from app.services.game import ClubService
from app.services.player_contracts import ContractService
from app.services.player_development import TrainingService


def add_club(name="Clube humano"):
    repo = GameRepository(app.state.database)
    user = SimpleNamespace(id=str(ObjectId()))
    club = ClubService(repo).create(user, ClubInput(name=name, country_id="BR", badge_id="blue"))
    return user, club


def test_division_bots_random_players_and_schedule(client):
    headers = account(client, 1)
    club = create(client, headers)
    db = app.state.database
    table = client.get("/api/competition", headers=headers).json()
    assert table["division"]["name"] == "A"
    assert len(table["standings"]) == 20
    assert sum(row["is_bot"] for row in table["standings"]) == 19
    players = client.get("/api/training", headers=headers).json()
    assert len(players) == 25
    assert {p["position"] for p in players} == {"GK", "FB", "CB", "MID", "ATT"}
    assert len({p["strength"] for p in players}) > 1
    assert all(p["training_progress"] == 0 and p["disease"] is None for p in players)
    assert db.matches.count_documents({}) == 380
    matches = client.get("/api/competition/matches", headers=headers).json()
    assert len(matches) == 38
    assert sum(m["home_club_id"] == club["id"] for m in matches) == 19
    assert len(client.get("/api/calendar?type=match", headers=headers).json()) == 38
    assert len(client.get("/api/youth", headers=headers).json()) == 3


def test_bot_replacement_inherits_sport_only_and_keeps_audit(client):
    add_club()
    db = app.state.database
    bot = db.standings.find_one({"is_bot": True}, sort=[("position", -1)])
    inherited = {
        "games": 7,
        "wins": 1,
        "draws": 2,
        "losses": 4,
        "goals_for": 5,
        "goals_against": 12,
        "goal_difference": -7,
        "points": 5,
    }
    db.standings.update_one({"_id": bot["_id"]}, {"$set": inherited})
    historical = db.matches.find_one({"home_slot_id": bot["_id"]})
    db.matches.update_one(
        {"_id": historical["_id"]},
        {"$set": {"status": "completed", "result": {"historical": True}}},
    )
    _, newcomer = add_club("Novo clube")
    slot = db.season_clubs.find_one({"club_id": ObjectId(newcomer["id"])})
    assert slot["_id"] == bot["_id"]
    row = db.standings.find_one({"_id": slot["_id"]})
    assert all(row[key] == value for key, value in inherited.items())
    assert row["position"] == bot["position"]
    saved = db.matches.find_one({"_id": historical["_id"]})
    assert saved["home_club_id"] == bot["club_id"]
    assert saved["result"] == {"historical": True}
    assert (
        db.matches.count_documents(
            {
                "status": "scheduled",
                "home_slot_id": slot["_id"],
                "home_club_id": {"$ne": ObjectId(newcomer["id"])},
            }
        )
        == 0
    )
    audit = db.club_replacements.find_one({"new_club_id": ObjectId(newcomer["id"])})
    assert audit["old_club_id"] == bot["club_id"]
    assert audit["inherited_standing"]["points"] == 5
    assert db.players.count_documents({"current_club_id": ObjectId(newcomer["id"])}) == 25
    assert db.club_finances.find_one({"_id": ObjectId(newcomer["id"])})["balance"] == 10000000
    assert db.clubs.find_one({"_id": bot["club_id"]})["active"] is False


def test_concurrent_joins_replace_distinct_bots(client):
    add_club()
    with ThreadPoolExecutor(max_workers=2) as executor:
        clubs = list(executor.map(lambda i: add_club(f"Clube {i}")[1], range(2)))
    db = app.state.database
    audits = list(db.club_replacements.find({}))
    assert len(audits) == 2
    assert len({r["old_club_id"] for r in audits}) == 2
    assert db.season_clubs.count_documents({"is_bot": False}) == 3
    assert {r["new_club_id"] for r in audits} == {ObjectId(c["id"]) for c in clubs}


def test_full_division_creates_next_and_highest_available_is_used(client):
    for i in range(20):
        add_club(f"Humano {i}")
    _, lower = add_club("Primeiro da B")
    db = app.state.database
    assert db.divisions.count_documents({}) == 2
    assert db.clubs.find_one({"_id": ObjectId(lower["id"])})["division_tier"] == 1
    assert db.season_clubs.count_documents({"is_bot": False}) == 21
    assert db.matches.count_documents({}) == 760
    _, next_club = add_club("Segundo da B")
    assert db.clubs.find_one({"_id": ObjectId(next_club["id"])})["division_tier"] == 1
    assert db.divisions.count_documents({}) == 2


def test_training_youth_promotion_and_permissions(client):
    headers, stranger = account(client, 1), account(client, 2)
    create(client, headers)
    create(client, stranger)
    player = client.get("/api/training", headers=headers).json()[0]
    db = app.state.database
    db.player_training.insert_one({"_id": ObjectId(player["id"]), "progress": 99})
    trained = client.post(f"/api/players/{player['id']}/train", headers=headers)
    assert trained.status_code == 200
    assert (
        trained.json()["individual_skills"]["goalkeeping"]
        == player["individual_skills"]["goalkeeping"] + 1
    )
    assert trained.json()["training_progress"] == 0
    assert trained.json()["overall"] == trained.json()["strength"]
    assert client.post(f"/api/players/{player['id']}/train", headers=stranger).status_code == 403
    assert client.post("/api/players/invalid/train", headers=headers).status_code == 404
    youth = client.get("/api/youth", headers=headers).json()[0]
    assert 14 <= youth["age"] <= 17
    assert client.post(f"/api/youth/{youth['id']}/select", headers=headers).status_code == 200
    assert client.post(f"/api/players/{youth['id']}/train", headers=headers).status_code == 200
    assert client.post(f"/api/youth/{youth['id']}/promote", headers=headers).status_code == 409
    db.youth_players.update_one({"_id": ObjectId(youth["id"])}, {"$set": {"age": 18}})
    assert client.post(f"/api/youth/{youth['id']}/promote", headers=stranger).status_code == 403
    assert client.post(f"/api/youth/{youth['id']}/promote", headers=headers).status_code == 200
    assert client.post(f"/api/youth/{youth['id']}/promote", headers=headers).status_code == 409
    assert len(client.get("/api/youth", headers=headers).json()) == 0
    squad = client.get("/api/squad", headers=headers).json()
    assert len(squad["players"]) == 26
    assert youth["id"] in squad["lineup"]["reserves"]


def test_concurrent_training_loses_no_clicks(client):
    user, club = add_club()
    repo = GameRepository(app.state.database)
    player = repo.find("players", {"current_club_id": ObjectId(club["id"])})
    app.state.database.player_training.insert_one({"_id": player["_id"], "progress": 98})
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(
            executor.map(lambda _: TrainingService(repo).train(user, str(player["_id"])), range(2))
        )
    final = repo.find("players", {"_id": player["_id"]})
    assert app.state.database.player_training.find_one({"_id": player["_id"]})["progress"] == 0
    assert (
        final["individual_skills"]["goalkeeping"] == player["individual_skills"]["goalkeeping"] + 1
    )


def test_match_runs_offline_with_persisted_snapshot_once(client):
    _, club = add_club()
    db, repo = app.state.database, GameRepository(app.state.database)
    match = db.matches.find_one({"home_club_id": ObjectId(club["id"])})
    service = CompetitionService(repo)
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: service.play(match["_id"], match["date"]), range(2)))
    saved = db.matches.find_one({"_id": match["_id"]})
    assert saved["status"] == "completed"
    assert saved["result"]["snapshot"]["seed"] == match["seed"]
    assert len(saved["result"]["snapshot"]["home"]["lineup"]) == 11
    for side in ("home", "away"):
        assert db.standings.find_one({"_id": match[f"{side}_slot_id"]})["games"] == 1
    before = list(db.standings.find({}).sort("_id", 1))
    service.play(match["_id"], match["date"])
    assert list(db.standings.find({}).sort("_id", 1)) == before


def test_season_finalization_plays_all_matches_ages_and_is_idempotent(client):
    user, club = add_club()
    db, repo = app.state.database, GameRepository(app.state.database)
    season = CompetitionService.current(repo)
    player = repo.find("players", {"current_club_id": ObjectId(club["id"])})
    youth = repo.find("youth_players", {"current_club_id": ObjectId(club["id"])})
    bot = db.clubs.find_one({"is_bot": True, "active": True})
    lineup = db.lineups.find_one({"_id": bot["_id"]})
    free = db.players.find_one({"_id": {"$in": lineup["reserves"]}, "position": "GK"})
    repo.transaction(lambda tx: ContractService.terminate(tx, free["_id"]))
    db.players.update_one(
        {"_id": free["_id"]}, {"$set": {"current_club_id": None, "owner_club_id": None}}
    )
    junior = db.youth_players.find_one({"current_club_id": bot["_id"]})
    db.youth_players.update_one(
        {"_id": junior["_id"]},
        {
            "$set": {
                "age": 18,
                "position": "MID",
                "strength": 65,
                "overall": 65,
                "individual_skills": {
                    skill: 65
                    for skill in (
                        "goalkeeping",
                        "speed",
                        "technique",
                        "passing",
                        "tackling",
                        "playmaking",
                        "finishing",
                    )
                },
            }
        },
    )
    important = db.player_contracts.find_one({"player_id": lineup["starters"][0]})
    db.player_contracts.update_one(
        {"_id": important["_id"]},
        {
            "$set": {
                "expiring_at": season["starts_at"],
                "expires_at": season["starts_at"] + timedelta(days=3),
            }
        },
    )
    finalizer = SeasonFinalizationService(repo)
    finalizer.finalize(season["_id"], season["ends_at"])
    finalizer.finalize(season["_id"], season["ends_at"])
    completed = repo.find("seasons", {"_id": season["_id"]})
    assert completed["status"] == "completed"
    assert db.matches.count_documents({"season_id": season["_id"], "status": "completed"}) == 380
    old_rows = list(db.standings.find({"season_id": season["_id"]}))
    assert all(row["games"] == 38 for row in old_rows)
    assert all(row["wins"] + row["draws"] + row["losses"] == 38 for row in old_rows)
    assert all(row["points"] == row["wins"] * 3 + row["draws"] for row in old_rows)
    assert (
        sum(
            t["name"] == "Campeão da Série A"
            for t in db.clubs.find_one({"_id": completed["champion_club_id"]})["trophies"]
        )
        == 1
    )
    assert repo.find("players", {"_id": player["_id"]})["age"] == player["age"] + 1
    assert repo.find("youth_players", {"_id": youth["_id"]})["age"] == youth["age"] + 1
    assert len(TrainingService(repo).get(user, youth=True)) == 3
    assert db.seasons.count_documents({"status": "active"}) == 1
    bots = list(db.clubs.find({"is_bot": True, "active": True}))
    assert not db.club_finances.find_one(
        {"_id": {"$in": [b["_id"] for b in bots]}, "balance": {"$lt": 0}}
    )
    for checked_bot in bots:
        lineup = db.lineups.find_one({"_id": checked_bot["_id"]})
        assert len(lineup["starters"]) == 11
        assert len(set(lineup["starters"])) == 11
        assert (
            db.players.count_documents(
                {
                    "_id": {"$in": lineup["starters"]},
                    "current_club_id": checked_bot["_id"],
                    "status": {"$nin": ["retired", "injured", "suspended"]},
                }
            )
            == 11
        )
    assert db.bot_decisions.count_documents({"decision_type": "training"}) > 0
    # Similar, rested squads may keep balanced pre-game tactics; in-match changes
    # remain real tactical decisions and are recorded by the production engine.
    assert (
        db.bot_decisions.count_documents({"decision_type": "tactics"}) > 0
        or db.matches.count_documents(
            {
                "season_id": season["_id"],
                "result.events": {
                    "$elemMatch": {
                        "type": "play_style_change",
                        "team_id": {"$in": [str(b["_id"]) for b in bots]},
                    }
                },
            }
        )
        > 0
    )
    assert (
        db.bot_decisions.count_documents({"club_id": bot["_id"], "decision_type": "free_agent"}) > 0
    )
    assert (
        db.bot_decisions.count_documents(
            {"club_id": bot["_id"], "decision_type": "youth_promotion"}
        )
        > 0
    )
    assert (
        db.bot_decisions.count_documents({"club_id": bot["_id"], "decision_type": "contract"}) > 0
    )
    upcoming = CompetitionService.current(repo)
    assert upcoming["number"] == 2
    assert upcoming["starts_at"] == season["ends_at"]
    assert db.matches.count_documents({"season_id": upcoming["_id"]}) == 380


def test_promotion_relegation_and_retirement_are_idempotent(client):
    user, club = add_club()
    db, repo = app.state.database, GameRepository(app.state.database)
    season = CompetitionService.current(repo)
    service = CompetitionService(repo)
    division = repo.insert("divisions", {"_id": ObjectId(), "tier": 1, "name": "B"})
    config = service.season_config(season)
    slots = [
        service.add_slot(repo, season, division, service.create_bot(repo, 1, i, config))
        for i in range(20)
    ]
    service.schedule(repo, season, division, slots)
    db.matches.update_many({}, {"$set": {"status": "completed"}})
    division_a = db.divisions.find_one({"tier": 0})
    old_a = list(db.standings.find({"division_id": division_a["_id"]}).sort("position", 1))
    old_b = list(db.standings.find({"division_id": division["_id"]}).sort("position", 1))
    retiree = repo.find("players", {"current_club_id": ObjectId(club["id"])})
    db.players.update_one({"_id": retiree["_id"]}, {"$set": {"age": 34}})
    db.seasons.update_one(
        {"_id": season["_id"]},
        {
            "$set": {
                "config.DECLINE_PROBABILITIES": [[35, 1]],
                "config.RETIREMENT_PROBABILITIES": [[35, 1]],
            }
        },
    )
    finalizer = SeasonFinalizationService(repo)
    finalizer.finalize(season["_id"], season["ends_at"])
    finalizer.finalize(season["_id"], season["ends_at"])
    assert all(db.clubs.find_one({"_id": r["club_id"]})["division_tier"] == 1 for r in old_a[-4:])
    assert all(db.clubs.find_one({"_id": r["club_id"]})["division_tier"] == 0 for r in old_b[:4])
    assert all(db.clubs.find_one({"_id": r["club_id"]})["division_tier"] == 1 for r in old_b[4:])
    upcoming = service.current(repo)
    for d in (division_a, division):
        assert (
            db.season_clubs.count_documents({"season_id": upcoming["_id"], "division_id": d["_id"]})
            == 20
        )
    retired = repo.find("players", {"_id": retiree["_id"]})
    assert retired["age"] == 35 and retired["status"] == "retired"
    assert retired["strength"] == retiree["strength"] - 1
    assert retiree["_id"] not in repo.find("lineups", {"_id": ObjectId(club["id"])})["starters"]
    assert str(retiree["_id"]) not in {p["id"] for p in TrainingService(repo).get(user)}
    with pytest.raises(HTTPException) as error:
        TrainingService(repo).train(user, str(retiree["_id"]))
    assert error.value.status_code == 409


def test_transfer_window_boundaries(client):
    add_club()
    repo = GameRepository(app.state.database)
    season = CompetitionService.current(repo)
    for day, allowed in [
        (0, True),
        (1.999, True),
        (2, False),
        (14.999, False),
        (15, True),
        (16.999, True),
        (17, False),
        (30, False),
    ]:
        now = season["starts_at"] + timedelta(days=day)
        if allowed:
            repo.transaction(lambda active: CompetitionService.require_transfer_window(active, now))
        else:
            with pytest.raises(HTTPException) as error:
                repo.transaction(
                    lambda active: CompetitionService.require_transfer_window(active, now)
                )
            assert error.value.status_code == 409


def test_transfer_acceptance_enforces_windows_without_partial_writes(client, monkeypatch):
    from test_game import listing_offer

    seller, buyer = account(client, 1), account(client, 2)
    first, second = create(client, seller), create(client, buyer)
    player, _, offer = listing_offer(client, (seller, buyer, first, second))
    repo = GameRepository(app.state.database)
    season = CompetitionService.current(repo)
    assert (
        client.post(f"/api/market/offers/{offer['id']}/accept", headers=seller).status_code == 200
    )
    repo.update(
        "transfer_offers",
        {"_id": ObjectId(offer["id"])},
        {"$set": {"expires_at": season["starts_at"] + timedelta(days=16)}},
    )
    monkeypatch.setattr(
        "app.services.negotiation.utcnow", lambda: season["starts_at"] + timedelta(days=2)
    )
    assert (
        client.post(f"/api/market/negotiations/{offer['id']}/confirm", headers=buyer).status_code
        == 409
    )
    assert repo.find("players", {"_id": ObjectId(player["id"])})["current_club_id"] == ObjectId(
        first["id"]
    )
    assert repo.find("club_finances", {"_id": ObjectId(second["id"])})["balance"] == 10000000
    monkeypatch.setattr(
        "app.services.negotiation.utcnow", lambda: season["starts_at"] + timedelta(days=15)
    )
    assert (
        client.post(f"/api/market/negotiations/{offer['id']}/confirm", headers=buyer).status_code
        == 200
    )


def test_old_positions_and_overall_remain_compatible(client):
    from app.config.game import legacy_position
    from app.schemas.game import LineupInput
    from app.services.game import SquadService

    user, club = add_club()
    repo = GameRepository(app.state.database)
    cid = ObjectId(club["id"])
    for player in repo.many("players", {"current_club_id": cid}, limit=None):
        repo.update(
            "players",
            {"_id": player["_id"]},
            {
                "$set": {"position": legacy_position(player["position"])},
                "$unset": {"strength": "", "training_level": "", "status": ""},
            },
        )
    squad = SquadService(repo).get(user)
    SquadService(repo).save(
        user,
        LineupInput(**{key: squad["lineup"][key] for key in ("formation", "starters", "reserves")}),
    )
    player = squad["players"][0]
    result = TrainingService(repo).train(user, player["id"])
    assert result["strength"] == player["overall"] and result["training_progress"] == 1
    assert len(CompetitionService.match_team(repo, cid).lineup) == 11


def test_finalization_failure_rolls_back_and_can_resume(client, monkeypatch):
    from app.services.player_development import PlayerAgingService

    _, club = add_club()
    db, repo = app.state.database, GameRepository(app.state.database)
    season = CompetitionService.current(repo)
    db.matches.update_many({}, {"$set": {"status": "completed"}})
    player = repo.find("players", {"current_club_id": ObjectId(club["id"])})
    original = PlayerAgingService.process

    def fail_after_aging(self, active, identity, config):
        original(self, active, identity, config)
        raise RuntimeError("Injected failure")

    monkeypatch.setattr(PlayerAgingService, "process", fail_after_aging)
    with pytest.raises(RuntimeError):
        SeasonFinalizationService(repo).finalize(season["_id"], season["ends_at"])
    assert db.seasons.count_documents({}) == 1
    assert CompetitionService.current(repo)["_id"] == season["_id"]
    assert repo.find("players", {"_id": player["_id"]})["age"] == player["age"]
    assert not any(
        t["name"] == "Campeão da Série A"
        for c in repo.many("clubs", {}, limit=None)
        for t in c["trophies"]
    )
    assert (
        sum(
            t["name"] == "Copa Nacional"
            for c in repo.many("clubs", {}, limit=None)
            for t in c["trophies"]
        )
        == 1
    )
    monkeypatch.setattr(PlayerAgingService, "process", original)
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(
            executor.map(
                lambda _: SeasonFinalizationService(repo).finalize(
                    season["_id"], season["ends_at"]
                ),
                range(2),
            )
        )
    assert repo.find("players", {"_id": player["_id"]})["age"] == player["age"] + 1
    assert db.seasons.count_documents({}) == 2
    assert sum(len(c["trophies"]) for c in repo.many("clubs", {}, limit=None)) == 2


def test_existing_club_bootstrap_preserves_administrative_data(client):
    user, club = add_club()
    db, repo = app.state.database, GameRepository(app.state.database)
    cid = ObjectId(club["id"])
    original_players = list(db.players.find({"current_club_id": cid}).sort("_id", 1))
    original_balance = repo.find("club_finances", {"_id": cid})["balance"]
    # Model a pre-script-4 database retaining the original club structure.
    for collection in (
        "seasons",
        "divisions",
        "season_clubs",
        "standings",
        "matches",
        "youth_players",
        "youth_batches",
    ):
        db[collection].delete_many({})
    db.clubs.delete_many({"is_bot": True})
    db.calendar_events.delete_many({"type": "match"})
    CompetitionService(repo).bootstrap()
    CompetitionService(repo).bootstrap()
    assert db.season_clubs.count_documents({"club_id": cid}) == 1
    assert list(db.players.find({"current_club_id": cid}).sort("_id", 1)) == original_players
    assert repo.find("club_finances", {"_id": cid})["balance"] == original_balance
    assert len(TrainingService(repo).get(user, youth=True)) == 3
    assert db.matches.count_documents({}) == 380
