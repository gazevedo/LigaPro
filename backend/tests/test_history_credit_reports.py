from datetime import timedelta

from bson import ObjectId
from test_game import account, create

from app.config.game import GameConfig
from app.main import app
from app.models.game import utcnow
from app.repositories.game import GameRepository
from app.services.bank_loans import BankLoanService
from app.services.competition import CompetitionService
from app.services.game_history import HistoryService
from app.services.monthly_finance import MonthlyFinanceService
from app.services.news import NewsService
from app.services.physical_condition import InjuryService
from app.services.player_development import PlayerAgingService


def setup(client):
    headers = account(client, 1)
    club = ObjectId(create(client, headers)["id"])
    return headers, club, GameRepository(app.state.database)


def test_credit_installments_limits_arbitrage_and_settlement(client):
    h, club, repo = setup(client)
    available = client.get("/api/finance/bank", headers=h).json()["credit_limit"]
    assert available > 0
    assert (
        client.post(
            "/api/finance/loans/short_term", headers=h, json={"amount": available + 1}
        ).status_code
        == 409
    )
    created = client.post("/api/finance/loans/short_term", headers=h, json={"amount": 1000000})
    assert created.status_code == 201, created.text
    loan = created.json()
    assert loan["remaining_balance"] == 1090000 and loan["installment_value"] == 363334
    assert (
        client.post("/api/finance/bank/investment", headers=h, json={"amount": 10000}).status_code
        == 409
    )
    before = repo.find("club_finances", {"_id": club})["balance"]
    finance = repo.find("club_finances", {"_id": club})
    MonthlyFinanceService.process_due(repo, finance["next_month_at"])
    after = repo.find("club_loans", {"_id": ObjectId(loan["id"])})
    assert after["remaining_balance"] == 726666
    assert repo.find("club_finances", {"_id": club})["balance"] < before + 1500000
    MonthlyFinanceService.process_due(repo, finance["next_month_at"])
    assert repo.find("club_loans", {"_id": after["_id"]})["remaining_balance"] == 726666
    settled = client.post(f"/api/finance/loans/{loan['id']}/settle", headers=h)
    assert settled.status_code == 200 and settled.json()["remaining_balance"] == 0
    assert client.post(f"/api/finance/loans/{loan['id']}/settle", headers=h).status_code == 409


def test_credit_default_blocks_and_repayment_recovers(client):
    h, club, repo = setup(client)
    loan = repo.transaction(lambda tx: BankLoanService.contract(tx, club, "medium_term", 1000000))
    end = repo.find("club_finances", {"_id": club})["next_month_at"]
    period = timedelta(seconds=repo.find("club_finances", {"_id": club})["month_seconds"])
    repo.update("club_finances", {"_id": club}, {"$set": {"balance": 0}})
    repo.transaction(lambda tx: BankLoanService.monthly(tx, club, end, period))
    assert client.get("/api/finance/bank", headers=h).json()["credit_blocked"]
    assert (
        client.post("/api/finance/loans/short_term", headers=h, json={"amount": 10000}).status_code
        == 409
    )
    repo.transaction(lambda tx: tx.money(club, 2000000, "other_income"))
    assert client.post(f"/api/finance/loans/{loan['id']}/settle", headers=h).status_code == 200
    assert not client.get("/api/finance/bank", headers=h).json()["credit_blocked"]


def test_actual_news_and_season_history_are_immutable(client):
    h, club, repo = setup(client)
    season = CompetitionService.current(repo)
    player = repo.find("players", {"current_club_id": club})
    match = {"_id": ObjectId(), "date": utcnow(), "home_club_id": club}
    event = {
        "type": "injury",
        "player_id": str(player["_id"]),
        "team_id": str(club),
        "severity": "minor",
        "injury_type": "contusão",
    }
    repo.transaction(lambda tx: InjuryService.after_match(tx, match, {"events": [event]}))
    ref = ObjectId()
    for _ in range(2):
        repo.transaction(
            lambda tx: NewsService.publish(
                tx, "transfer", "Transferência confirmada", club, ref, player_id=player["_id"]
            )
        )
    assert repo.database.news_items.count_documents({"type": "transfer"}) == 1
    assert repo.database.news_items.count_documents({"type": "injury"}) == 1
    tables = {0: [{"club_id": club, "position": 1}]}
    repo.transaction(lambda tx: HistoryService.season(tx, season, tables, {club: 0}))
    repo.transaction(lambda tx: HistoryService.season(tx, season, tables, {club: 0}))
    assert repo.database.season_history.count_documents({}) == 1
    assert repo.database.news_items.count_documents({"type": "title"}) == 1
    repo.update("players", {"_id": player["_id"]}, {"$set": {"age": 90}})
    # Scope aging fixture to one player to exercise actual retirement hook.
    repo.update_many("players", {"_id": {"$ne": player["_id"]}}, {"$set": {"status": "retired"}})
    repo.update_many("youth_players", {}, {"$set": {"status": "promoted"}})
    repo.transaction(
        lambda tx: PlayerAgingService().process(
            tx, season["_id"], GameConfig(RETIREMENT_PROBABILITIES=((35, 1.0),))
        )
    )
    assert repo.database.news_items.count_documents({"type": "retirement"}) == 1
    next_season = {**season, "_id": ObjectId(), "number": season["number"] + 1}
    repo.transaction(lambda tx: HistoryService.season(tx, next_season, tables, {club: 0}))
    history = client.get("/api/history", headers=h).json()
    assert len(history["seasons"]) == 2 and len(history["clubs"]) == 2
    assert any(p["type"] == "retirement" for p in history["players"])


def test_postgame_is_the_persisted_result_projection(client):
    h, club, repo = setup(client)
    match = repo.find("matches", {"home_club_id": club})
    CompetitionService(repo).play(match["_id"], match["date"])
    stored = repo.find("matches", {"_id": match["_id"]})
    response = client.get(f"/api/competition/matches/{match['_id']}", headers=h)
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["statistics"] == stored["result"]["statistics"]
    projected = repo.many(
        "match_events", {"match_id": match["_id"]}, limit=None, sort=[("sequence", 1)]
    )
    assert [(e["type"], e["minute"]) for e in report["events"]] == [
        (e["type"], e["minute"]) for e in projected
    ]
    assert (
        report["financial"]["income"]
        == report["financial"]["attendance"] * report["financial"]["price"]
    )
    assert len(report["consequences"]) == len(report["ratings"])
    assert all(e["energy"] <= e["energy_before"] for e in report["consequences"])
    CompetitionService(repo).play(match["_id"], match["date"])
    assert repo.database.match_stats.count_documents({"match_id": match["_id"]}) == 1


def test_all_installments_settle_exact_interest_without_duplicate_debits(client):
    _, club, repo = setup(client)
    loan = repo.transaction(lambda tx: BankLoanService.contract(tx, club, "short_term", 1000000))
    for _ in range(3):
        end = repo.find("club_finances", {"_id": club})["next_month_at"]
        MonthlyFinanceService.process_due(repo, end)
        MonthlyFinanceService.process_due(repo, end)
    stored = repo.find("club_loans", {"_id": ObjectId(loan["id"])})
    payments = repo.many(
        "financial_transactions", {"club_id": club, "category": "loan_installment"}, limit=None
    )
    assert stored["remaining_balance"] == 0 and stored["status"] == "settled"
    assert stored["paid_installments"] == 3 and len(payments) == 3
    assert sum(t["amount"] for t in payments) == -1090000
