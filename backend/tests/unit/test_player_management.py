from copy import deepcopy
from datetime import timedelta

from test_match_engine import team

from app.config.physical import PhysicalConfig
from app.models.game import utcnow
from app.services.market_value import MarketValueService
from app.services.match_engine import (
    MatchConfig,
    MatchEngine,
    MatchPlayer,
    PlayerEffectiveStrengthCalculator,
)
from app.services.physical_condition import PhysicalConditionService
from app.services.salary import SalaryService


def test_nonlinear_price_and_salary_curves_are_distinct():
    service = MarketValueService()
    player = {"strength": 50, "age": 27, "position": "CB", "owner_club_id": "club"}
    assert service.calculate(player, club={"reputation": 100}) == 690000
    assert SalaryService.reference(player) == 45000
    assert service.calculate({**player, "potential": 100}) == service.calculate(player)
    assert service.calculate({**player, "strength": 100, "stars": 5}) <= 12000000
    assert service.calculate({**player, "strength": 1}) >= 50000
    prices = [
        service.asking_price({**player, "market_value": 1000000}, status)
        for status in ["listed", "available", "not_for_sale"]
    ]
    assert prices == [1000000, 1150000, 1750000]
    assert service.asking_price({**player, "owner_club_id": None}) == 0
    for seed in range(5):
        squad = [{**player, "strength": 40 + (i + seed) % 21} for i in range(25)]
        assert sum(SalaryService.normalize(squad)) == 1350000


def test_condition_factors_wear_and_elapsed_recovery():
    physical = PhysicalConfig()
    assert [physical.modifier(c) for c in [100, 85, 84, 70, 69, 55, 54, 40, 39, 0]] == [
        1,
        1,
        0.98,
        0.98,
        0.95,
        0.95,
        0.90,
        0.90,
        0.84,
        0.84,
    ]
    now = utcnow()
    player = {"age": 25, "physical_condition": 50, "energy": 80, "condition_updated_at": now}
    service = PhysicalConditionService()
    assert service.recover(player, now)["physical_condition"] == 50
    assert service.recover(player, now + timedelta(days=1))["physical_condition"] > 50
    assert service.recover(player, now + timedelta(days=100))["physical_condition"] == 100
    assert (
        service.recover({**player, "age": 40}, now + timedelta(days=1))["physical_condition"]
        < service.recover(player, now + timedelta(days=1))["physical_condition"]
    )
    assert service.wear(player, 120, "very_heavy") > service.wear(player, 90, "light")
    assert physical.risk(30, 40, "very_heavy") > physical.risk(100, 20, "light")
    calculator = PlayerEffectiveStrengthCalculator(MatchConfig(), "classic")
    fit = MatchPlayer("p", "MID", "MID", physical_condition=100)
    neutral = calculator.calculate(fit, "passing")
    fit.physical_condition = 30
    assert abs(calculator.calculate(fit, "passing") / neutral - 0.84) < 1e-9


def test_injury_events_remove_players_and_bots_replace_them():
    home, away = team("h", is_bot=True), team("a", is_bot=True)
    home.reserves = [MatchPlayer("h-reserve", "MID", "MID")]
    engine = MatchEngine(physical_config=PhysicalConfig(injury_probability=1))
    result = engine.simulate(home, away, 3)
    assert result == engine.simulate(home, away, 3)
    injuries = [e for e in result["events"] if e["type"] == "injury"]
    assert injuries
    for event in injuries:
        assert event["matches_out"] in range(1, 13)
        late = [
            e
            for e in result["events"]
            if e["minute"] > event["minute"] and e.get("player_id") == event["player_id"]
        ]
        assert not late
    assert home.lineup == deepcopy(home.lineup)


def test_neutral_condition_and_disabled_injuries_preserve_seeded_engine():
    home, away = team("h"), team("a")
    engine = MatchEngine(physical_config=PhysicalConfig(injury_probability=0))
    first = engine.simulate(home, away, 42)
    for player in home.lineup + away.lineup:
        player.age = 40
    second = engine.simulate(home, away, 42)
    assert first["score"] == second["score"]
    assert first["events"] == second["events"]
