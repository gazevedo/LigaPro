from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.models.game import utcnow
from app.services.bank_loans import BankLoanService
from app.services.game import FinanceService
from app.services.sponsorship import SponsorshipService


def loan_repo():
    now = utcnow()
    loan = {
        "_id": ObjectId(),
        "club_id": ObjectId(),
        "status": "active",
        "remaining_balance": 900,
        "installment_value": 300,
        "paid_installments": 0,
        "next_installment_at": now,
    }
    repo = Mock()
    repo.document.return_value = loan
    repo.find.return_value = loan
    return repo, loan, now


def test_due_installment_overdraws_cash_and_advances_once():
    repo, loan, now = loan_repo()
    balance = 100

    def money(club_id, amount, category, reference, **kwargs):
        nonlocal balance
        assert kwargs["allow_overdraft"] is True
        balance += amount

    def update(collection, query, changes):
        if collection == "club_loans":
            loan.update(changes["$set"])
            loan["paid_installments"] += changes["$inc"]["paid_installments"]

    repo.money.side_effect = money
    repo.update.side_effect = update
    repo.many.side_effect = lambda *a, **k: (
        [deepcopy(loan)] if loan["next_installment_at"] <= now else []
    )
    with patch.object(BankLoanService, "credit", return_value={}):
        BankLoanService.monthly(repo, loan["club_id"], now, timedelta(days=2))
        BankLoanService.monthly(repo, loan["club_id"], now, timedelta(days=2))
    assert balance == -200
    assert loan["remaining_balance"] == 600 and loan["paid_installments"] == 1
    repo.money.assert_called_once()


@pytest.mark.parametrize("payment,remaining", [(200, 700), (900, 0), (None, 0)])
def test_advance_payment_reduces_balance_and_preserves_schedule(payment, remaining):
    repo, loan, now = loan_repo()
    with patch.object(BankLoanService, "credit", return_value={}):
        BankLoanService.settle(repo, loan["club_id"], str(loan["_id"]), payment)
    changes = repo.update.call_args_list[0].args[2]["$set"]
    assert changes["remaining_balance"] == remaining
    assert changes["status"] == ("settled" if remaining == 0 else "active")
    assert "next_installment_at" not in changes and "paid_installments" not in changes
    assert loan["next_installment_at"] == now
    assert repo.money.call_args.args[1] == -(900 if payment is None else payment)
    assert repo.money.call_args.kwargs["allow_overdraft"] is True


@pytest.mark.parametrize("amount", [0, -1, 901])
def test_advance_payment_rejects_invalid_amounts(amount):
    repo, loan, _ = loan_repo()
    with pytest.raises(HTTPException) as error:
        BankLoanService.settle(repo, loan["club_id"], str(loan["_id"]), amount)
    assert error.value.status_code == 422
    repo.money.assert_not_called()


def test_sponsor_inherited_from_bot_can_end_but_new_contract_cannot():
    now = utcnow()
    club = {"_id": ObjectId(), "claimed_at": now}
    contract = {
        "_id": ObjectId(),
        "club_id": club["_id"],
        "status": "active",
        "starts_at": now - timedelta(days=1),
        "ends_at": now + timedelta(days=20),
    }
    repo = Mock()
    repo.document.return_value = contract
    repo.update.return_value = contract
    SponsorshipService.terminate(repo, club, str(contract["_id"]), now)
    assert repo.update.call_args.args[2]["$set"] == {
        "status": "terminated",
        "ends_at": now,
        "terminated_at": now,
    }
    contract["starts_at"] = now + timedelta(seconds=1)
    assert not SponsorshipService.can_terminate(club, contract)
    with pytest.raises(HTTPException):
        SponsorshipService.terminate(repo, club, str(contract["_id"]), now)


def test_sponsor_termination_checks_owner():
    repo = Mock()
    repo.document.return_value = {"club_id": ObjectId()}
    with pytest.raises(HTTPException) as error:
        SponsorshipService.terminate(repo, {"_id": ObjectId()}, str(ObjectId()))
    assert error.value.status_code == 403


def test_ticketing_enriches_history_and_projects_next_home_game_without_writes():
    repo = Mock()
    now = utcnow()
    club = {"_id": "home", "name": "Aurora"}
    last = {
        "_id": "last",
        "home_club_id": "home",
        "away_club_id": "away",
        "date": now - timedelta(days=1),
        "status": "completed",
        "home_goals": 2,
        "away_goals": 0,
    }
    future = {**last, "_id": "next", "date": now + timedelta(days=1), "status": "scheduled"}
    repo.owned.return_value = club
    repo.find.return_value = {"ticket_price": 2000, "capacity": 10000}
    history = [{"_id": "ticket", "match_id": "last", "attendance": 50, "income": 100000}]

    def many(collection, query, **kwargs):
        if collection == "ticket_history":
            assert kwargs["sort"] == [("created_at", -1)]
            return history
        if collection == "matches":
            return [last] if "_id" in query else [future]
        if collection == "clubs":
            return [club, {"_id": "away", "name": "Estrela"}]
        return []

    repo.many.side_effect = many
    repo.ticket_income.return_value = 100000
    with patch(
        "app.services.game.FanBaseService.sector_ticketing",
        return_value=[{"attendance": 70, "income": 140000}],
    ):
        result = FinanceService(repo).tickets(SimpleNamespace(id="user"))
    assert result["last_match"]["match"]["home_goals"] == 2
    assert result["history"][0]["match"]["away_name"] == "Estrela"
    assert result["next_match"]["id"] == "next"
    assert result["estimated_income"] == 140000
    assert result["estimated_attendance"] == 70
    repo.update.assert_not_called()
    repo.money.assert_not_called()


def test_legacy_loan_partial_settlement_preserves_unpaid_balance():
    repo = Mock()
    club_id, loan_id = ObjectId(), ObjectId()
    repo.owned.return_value = {"_id": club_id}
    repo.document.return_value = {
        "_id": loan_id,
        "club_id": club_id,
        "type": "bank_loan",
        "status": "active",
        "amount": 1000,
        "interest": 100,
    }
    repo.transaction.side_effect = lambda callback: callback(repo)
    repo.update.return_value = {}
    FinanceService(repo).settle(SimpleNamespace(id="user"), str(loan_id), 200)
    repo.money.assert_called_once_with(
        club_id, -200, "bank_settlement", loan_id, allow_overdraft=True
    )
    assert repo.update.call_args.args[2]["$set"]["remaining_balance"] == 900
    assert repo.update.call_args.args[2]["$set"]["status"] == "active"


def test_legacy_due_payment_is_debited_on_due_date_even_without_cash():
    from app.services.game import process_due

    repo = Mock()
    now = utcnow()
    loan = {
        "_id": ObjectId(),
        "club_id": ObjectId(),
        "type": "bank_loan",
        "status": "active",
        "amount": 1000,
        "interest": 100,
        "remaining_balance": 700,
        "ends_at": now,
    }
    repo.many.side_effect = lambda collection, *args, **kwargs: (
        [loan] if collection == "bank_contracts" else []
    )
    repo.find.return_value = loan
    repo.transaction.side_effect = lambda callback: callback(repo)
    with (
        patch("app.services.game.ClubService.complete_pending_creations"),
        patch("app.services.game.CompetitionService.process_due"),
        patch("app.services.game.MonthlyFinanceService.process_due"),
        patch("app.services.game.ContractService.process_due"),
        patch("app.services.bot_manager.BotManagerService.process_due"),
        patch("app.services.negotiation.NegotiationService.expire"),
        patch("app.services.game.MarketService.return_loans"),
    ):
        process_due(repo)
    repo.money.assert_called_once_with(
        loan["club_id"],
        -700,
        "bank_settlement",
        loan["_id"],
        allow_overdraft=True,
        effective_at=now,
    )


def test_payroll_associates_position_and_shirt_number_with_the_correct_player():
    from app.services.player_contracts import ContractService

    now = utcnow()
    contracts = [
        {
            "player_id": identity,
            "salary": 100,
            "expires_at": now + timedelta(days=1),
            "paid_until": now,
            "salary_period_seconds": 86400,
            "status": "active",
        }
        for identity in ("first", "second")
    ]
    players = [
        {"_id": "second", "name": "Atacante", "position": "ATT", "shirt_number": 9},
        {"_id": "first", "name": "Goleiro", "position": "GK", "shirt_number": 1},
    ]
    repo = Mock()
    repo.many.side_effect = lambda collection, *args, **kwargs: (
        contracts
        if collection == "player_contracts"
        else players
        if collection == "players"
        else []
    )
    rows = ContractService(repo).finance("club")["salary_costs"]
    assert [(row["name"], row["position"], row["shirt_number"]) for row in rows] == [
        ("Goleiro", "GK", 1),
        ("Atacante", "ATT", 9),
    ]
