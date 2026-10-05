from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from bson import ObjectId
from test_game import account, create

from app.main import app
from app.models.game import utcnow
from app.repositories.game import GameRepository
from app.services.club_prestige import ClubRankingService, ClubReputationService
from app.services.competition import CompetitionService
from app.services.cup import CupService
from app.services.fan_base import FanBaseService
from app.services.monthly_finance import MonthlyFinanceService, bootstrap_economy
from app.services.player_contracts import ContractService


def setup(client):
    headers = account(client, 1)
    club = create(client, headers)
    return headers, ObjectId(club["id"]), GameRepository(app.state.database)


def test_new_humans_and_bots_have_equal_cash_and_normalized_payroll(client):
    headers, identity, repo = setup(client)
    for club in repo.many("clubs", {"active": {"$ne": False}}, limit=None):
        finance = repo.find("club_finances", {"_id": club["_id"]})
        assert finance["balance"] == finance["cash_balance"] == 10000000
        assert ContractService.payroll(repo, club["_id"]) == 1350000
        assert finance["monthly_fixed_revenue"] == 1500000
    public = client.get(f"/api/clubs/{identity}", headers=headers).json()
    assert public["supporters"] == 1000 and public["fan_satisfaction"] == 50
    assert "reputation" in public and "owner_user_id" not in public


def test_monthly_close_salary_summary_and_concurrent_idempotency(client):
    headers, identity, repo = setup(client)
    finance = repo.find("club_finances", {"_id": identity})
    now = finance["next_month_at"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: MonthlyFinanceService.process_due(repo, now), range(2)))
    ContractService(repo).process_due(now)
    MonthlyFinanceService.process_due(repo, now)
    assert repo.find("club_finances", {"_id": identity})["balance"] == 10150000
    assert repo.database.club_finance_months.count_documents({"club_id": identity}) == 1
    assert (
        repo.database.financial_transactions.count_documents(
            {"club_id": identity, "category": "sponsorship"}
        )
        == 1
    )
    assert (
        repo.database.financial_transactions.count_documents(
            {"club_id": identity, "category": "tv_rights"}
        )
        == 1
    )
    assert (
        repo.database.financial_transactions.count_documents(
            {"club_id": identity, "category": "salary"}
        )
        == 25
    )
    summary = client.get("/api/finance", headers=headers).json()
    assert summary["monthly_income"] == 1500000
    assert summary["monthly_expenses"] == 1350000
    assert summary["monthly_result"] == 150000
    assert summary["payroll_health"] == "atenção"


def test_fans_ranking_values_and_gate_are_updated_once(client):
    headers, identity, repo = setup(client)
    match = repo.find("matches", {"home_club_id": identity})
    before = repo.find("clubs", {"_id": identity})
    CompetitionService(repo).play(match["_id"], match["date"])
    after = repo.find("clubs", {"_id": identity})
    assert after["ranking_position"] > 0
    assert after["reputation"] == before["reputation"]
    gate = repo.find("ticket_history", {"match_id": match["_id"]})
    assert gate["attendance"] <= 10000 and gate["income"] == gate["attendance"] * 2000
    assert (
        repo.find(
            "financial_transactions", {"reference_id": match["_id"], "category": "ticketing"}
        )["amount"]
        == gate["income"]
    )
    assert repo.find(
        "player_market_value_history", {"reference_id": match["_id"], "reason": "round"}
    )
    count = repo.database.club_fan_history.count_documents({})
    CompetitionService(repo).play(match["_id"], match["date"])
    assert repo.database.club_fan_history.count_documents({}) == count
    assert repo.database.ticket_history.count_documents({"match_id": match["_id"]}) == 1
    assert client.get("/api/finance/tickets", headers=headers).json()["estimated_attendance"] >= 0


def test_title_increases_supporters_rank_and_slow_reputation(client):
    _, identity, repo = setup(client)
    before = repo.find("clubs", {"_id": identity})
    repo.transaction(
        lambda tx: FanBaseService.change(
            tx, identity, "title", ObjectId(), growth=0.08, satisfaction=10
        )
    )
    repo.transaction(lambda tx: ClubReputationService.season(tx, identity, 0, 1, True))
    after = repo.find("clubs", {"_id": identity})
    assert after["supporters"] > before["supporters"]
    assert 0 < after["reputation"] - before["reputation"] <= 3
    repo.update("clubs", {"_id": identity}, {"$set": {"recent_title_points": 100}})
    ClubRankingService.refresh(repo, CompetitionService.current(repo)["_id"], ObjectId())
    assert repo.find("club_ranking_history", {"club_id": identity})
    repo.transaction(
        lambda tx: FanBaseService.after_match(
            tx,
            {
                "_id": ObjectId(),
                "home_club_id": identity,
                "away_club_id": repo.find("clubs", {"is_bot": True})["_id"],
                "date": utcnow(),
            },
            2,
            0,
        )
    )
    assert repo.find("clubs", {"_id": identity})["fan_satisfaction"] > after["fan_satisfaction"]


def test_cup_bracket_offline_champion_prizes_calendar_and_repeat(client):
    headers, identity, repo = setup(client)
    season = CompetitionService.current(repo)
    cup = repo.transaction(lambda tx: CupService.ensure(tx, season))
    assert repo.database.competition_entries.count_documents({"competition_id": cup["_id"]}) == 20
    assert (
        len(repo.find("competition_rounds", {"competition_id": cup["_id"], "number": 1})["byes"])
        == 12
    )
    first = repo.find("competition_matches", {"competition_id": cup["_id"]})
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: CupService(repo).play(first["_id"], first["date"]), range(2)))
    CupService(repo).process_due(season, season["ends_at"])
    finished = repo.find("competitions", {"_id": cup["_id"]})
    assert finished["status"] == "completed"
    assert (
        repo.database.competition_matches.count_documents(
            {"competition_id": cup["_id"], "status": "completed"}
        )
        == 19
    )
    champion = repo.find("clubs", {"_id": finished["champion_club_id"]})
    assert any(t["name"] == "Copa Nacional" for t in champion["trophies"])
    assert (
        repo.find("financial_transactions", {"reference_id": cup["_id"], "category": "prize"})[
            "amount"
        ]
        == 1000000
    )
    assert repo.database.financial_transactions.count_documents({"category": "prize"}) == 20
    summary = client.get("/api/competition/cup", headers=headers).json()
    assert summary["entry"]["status"] in {"eliminated", "champion"}
    assert summary["matches"]
    played = summary["matches"][0]["id"]
    assert client.get(f"/api/competition/matches/{played}", headers=headers).status_code == 200
    events = client.get("/api/calendar", headers=headers).json()
    assert any(e["reference_id"] == played for e in events)
    snapshot = (repo.database.financial_transactions.count_documents({}), len(champion["trophies"]))
    CupService(repo).process_due(season, season["ends_at"])
    assert snapshot == (
        repo.database.financial_transactions.count_documents({}),
        len(repo.find("clubs", {"_id": champion["_id"]})["trophies"]),
    )


def test_bootstrap_preserves_cash_and_contracts(client):
    _, identity, repo = setup(client)
    repo.database.club_finances.update_one(
        {"_id": identity},
        {"$unset": {"next_month_at": "", "month_seconds": ""}, "$set": {"balance": 12345}},
    )
    before = list(repo.database.player_contracts.find({"club_id": identity}))
    bootstrap_economy(repo)
    bootstrap_economy(repo)
    assert repo.find("club_finances", {"_id": identity})["balance"] == 12345
    assert list(repo.database.player_contracts.find({"club_id": identity})) == before


def test_market_history_after_training_promotion_and_transfer(client):
    headers, identity, repo = setup(client)
    player = repo.find("players", {"current_club_id": identity})
    repo.update(
        "players",
        {"_id": player["_id"]},
        {
            "$set": {
                "strength": 49,
                "overall": 49,
                "individual_skills": {
                    key: 50
                    for key in (
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
    repo.database.player_training.insert_one({"_id": player["_id"], "progress": 99})
    response = client.post(f"/api/players/{player['_id']}/train", headers=headers)
    assert response.status_code == 200, response.text
    assert repo.find(
        "player_market_value_history", {"player_id": player["_id"], "reason": "training"}
    )
    youth = repo.find("youth_players", {"current_club_id": identity})
    repo.update("youth_players", {"_id": youth["_id"]}, {"$set": {"age": 18}})
    response = client.post(f"/api/youth/{youth['_id']}/promote", headers=headers)
    assert response.status_code == 200, response.text
    assert repo.find(
        "player_market_value_history", {"player_id": youth["_id"], "reason": "promotion"}
    )
    count = repo.database.player_market_value_history.count_documents({"player_id": player["_id"]})
    client.post(f"/api/players/{player['_id']}/train", headers=headers)
    assert (
        repo.database.player_market_value_history.count_documents({"player_id": player["_id"]})
        == count
    )


def test_five_season_finance_projection_without_unfunded_bots(client):
    _, identity, repo = setup(client)
    # Fixed-roster projection isolates economics from later bot recruitment/aging scripts.
    start = repo.find("club_finances", {"_id": identity})["finance_started_at"]
    repo.database.player_contracts.update_many(
        {}, {"$set": {"expires_at": start + timedelta(days=180)}}
    )
    now = max(
        f["finance_started_at"] for f in repo.many("club_finances", {}, limit=None)
    ) + timedelta(days=150, seconds=1)
    MonthlyFinanceService.process_due(repo, now)
    balances = [f["balance"] for f in repo.many("club_finances", {}, limit=None)]
    assert len(balances) == 20 and min(balances) == 19000000 and max(balances) == 19000000
    assert repo.database.club_finance_months.count_documents({}) == 1200
    before = sum(balances)
    MonthlyFinanceService.process_due(repo, now)
    assert sum(f["balance"] for f in repo.many("club_finances", {}, limit=None)) == before


def test_new_human_inherits_active_bot_cup_entry(client):
    _, identity, repo = setup(client)
    season = CompetitionService.current(repo)
    cup = repo.transaction(lambda tx: CupService.ensure(tx, season))
    headers = account(client, 2)
    club = create(client, headers, "Clube da copa")
    new_id = ObjectId(club["id"])
    replacement = repo.find("club_replacements", {"new_club_id": new_id})
    old_id = replacement["old_club_id"]
    assert repo.find("competition_entries", {"competition_id": cup["_id"], "club_id": new_id})
    assert not repo.find("competition_entries", {"competition_id": cup["_id"], "club_id": old_id})
    assert not repo.find(
        "competition_matches",
        {
            "competition_id": cup["_id"],
            "status": "scheduled",
            "$or": [{"home_club_id": old_id}, {"away_club_id": old_id}],
        },
    )
    assert not repo.find("competition_rounds", {"competition_id": cup["_id"], "byes": old_id})
