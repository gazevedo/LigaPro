from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from app.models.game import utcnow
from app.schemas.auth import RegisterRequest
from app.services.monthly_finance import MonthlyFinanceService


def test_monthly_breakdown_excludes_initial_funding_and_details_both_directions():
    repo = Mock()
    repo.rules.return_value = {}
    repo.many.return_value = []
    repo.find.side_effect = [
        {"balance": 1000, "next_month_at": utcnow()},
        {"category": "other_income", "amount": 100},
        {},
    ]
    repo.database.financial_transactions.aggregate.side_effect = [
        [
            {"_id": "other_income", "amount": 100, "income": 100, "expenses": 0},
            {"_id": "ticketing", "amount": 500, "income": 500, "expenses": 0},
            {"_id": "player_salary", "amount": -200, "income": 0, "expenses": 200},
        ],
        [],
    ]
    with patch("app.services.player_contracts.ContractService.payroll", return_value=200):
        result = MonthlyFinanceService.summary(repo, "club")
    assert result["income_details"] == [{"category": "ticketing", "amount": 500}]
    assert result["expense_details"] == [{"category": "player_salary", "amount": 200}]
    assert sum(row["amount"] for row in result["income_details"]) == result["monthly_income"]
    assert sum(row["amount"] for row in result["expense_details"]) == result["monthly_expenses"]


def test_registration_normalizes_stadium_name_and_rejects_whitespace():
    values = {"name": "Diretor", "email": "user@example.com", "password": "password123"}
    assert (
        RegisterRequest(**values, stadium_name=" Arena do Clube ").stadium_name == "Arena do Clube"
    )
    with pytest.raises(ValidationError):
        RegisterRequest(**values, stadium_name="   ")


def test_calendar_adds_both_team_names_and_the_home_stadium():
    from types import SimpleNamespace

    from app.services.game import CalendarService

    repo = Mock()
    repo.find.return_value = {"league_schedule_revision": 2}
    repo.owned.return_value = {"_id": "home"}
    values = {
        "calendar_events": [{"_id": "event", "reference_id": "match"}],
        "matches": [
            {"_id": "match", "status": "scheduled", "home_club_id": "home", "away_club_id": "away"}
        ],
        "clubs": [{"_id": "home", "name": "Aurora"}, {"_id": "away", "name": "Estrela"}],
        "stadiums": [{"_id": "home", "name": "Arena Aurora"}],
    }
    repo.many.side_effect = lambda collection, *args, **kwargs: values.get(collection, [])
    result = CalendarService(repo).get(
        SimpleNamespace(id="user"), SimpleNamespace(type=None, start=None, end=None)
    )
    assert result[0]["home_name"] == "Aurora"
    assert result[0]["away_name"] == "Estrela"
    assert result[0]["stadium_name"] == "Arena Aurora"
