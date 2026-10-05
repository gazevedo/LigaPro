import unittest
from copy import deepcopy
from datetime import timedelta

from test_match_engine import team

from app.config.economy import EconomyConfig, payroll_health, salary_weight
from app.config.market_value import MarketValueConfig
from app.models.game import utcnow
from app.services.club_prestige import ClubRankingService
from app.services.cup import bracket
from app.services.fan_base import FanBaseService
from app.services.market_value import MarketValueService
from app.services.match_engine import MatchConfig, MatchEngine
from app.services.player_statistics import match_player_summaries


class ClubEconomyTests(unittest.TestCase):
    def test_pricing_factors_and_configuration(self):
        service = MarketValueService()
        now = utcnow()
        player = {"strength": 60, "potential": 80, "age": 22, "position": "ATT"}
        contract = {"expires_at": now + timedelta(days=30), "salary_period_seconds": 216000}
        base = service.calculate(player, contract=contract, now=now)
        self.assertEqual(
            base, service.calculate({**player, "potential": 60}, contract=contract, now=now)
        )
        self.assertGreater(
            base, service.calculate({**player, "age": 38}, contract=contract, now=now)
        )
        self.assertGreater(service.calculate(player, contract=contract, rating=8, now=now), base)
        self.assertLess(service.calculate(player, contract=contract, rating=5, now=now), base)
        self.assertLess(
            service.calculate(
                player, contract={**contract, "expires_at": now + timedelta(days=1)}, now=now
            ),
            base,
        )
        self.assertGreater(
            service.calculate(player, club={"reputation": 80}, contract=contract, now=now), base
        )
        self.assertLess(
            service.calculate(player, club={"division_tier": 4}, contract=contract, now=now), base
        )
        self.assertAlmostEqual(
            MarketValueService(
                MarketValueConfig(
                    strength_curve=tuple((x, y * 2) for x, y in MarketValueConfig().strength_curve)
                )
            ).calculate(player, contract=contract, now=now),
            base * 2,
            delta=10000,
        )

    def test_attendance_price_capacity_and_satisfaction(self):
        club = {"supporters": 10000, "fan_satisfaction": 80, "reputation": 40}
        stadium = {"ticket_price": 2000, "capacity": 50000}
        normal = FanBaseService.attendance(club, stadium)
        self.assertLess(FanBaseService.attendance(club, stadium, price=8000), normal)
        self.assertLess(
            FanBaseService.attendance({**club, "fan_satisfaction": 10}, stadium), normal
        )
        self.assertEqual(FanBaseService.attendance(club, {**stadium, "capacity": 100}), 100)

    def test_ranking_recent_results_and_titles(self):
        row = {"position": 5, "points": 20, "tier": 0}
        normal = ClubRankingService.points({}, row, 1)
        self.assertGreater(ClubRankingService.points({}, row, 3), normal)
        self.assertGreater(ClubRankingService.points({"recent_title_points": 100}, row, 1), normal)
        self.assertLess(ClubRankingService.points({}, {**row, "tier": 2}, 1), normal)

    def test_economy_amounts_payroll_and_no_potential_in_salary(self):
        c = EconomyConfig()
        self.assertEqual(
            (c.STARTING_CASH, c.fixed_revenue, c.payroll_target), (10000000, 1500000, 1350000)
        )
        self.assertEqual(c.prize(1, 0), 2 * c.prize(2, 0))
        self.assertEqual(c.prize(2, 0), 2 * c.prize(3, 0))
        self.assertEqual(c.prize(1, 1), 6000000)
        self.assertEqual(
            [payroll_health(p, 100) for p in (80, 90, 110, 130)],
            ["saudável", "atenção", "alto risco", "crítico"],
        )
        player = {"strength": 50, "age": 25, "position": "ATT", "potential": 50}
        self.assertEqual(salary_weight(player), salary_weight({**player, "potential": 100}))

    def test_bracket_non_power_of_two(self):
        byes, pairs = bracket(list(range(20)), "seed")
        self.assertEqual(len(byes), 12)
        self.assertEqual(len(pairs), 4)
        self.assertEqual(set(byes + [p for pair in pairs for p in pair]), set(range(20)))
        self.assertEqual((byes, pairs), bracket(list(range(20)), "seed"))
        with self.assertRaises(ValueError):
            bracket([1, 1], "seed")

    def test_knockout_extra_time_shootout_and_actual_minutes(self):
        engine = MatchEngine(MatchConfig(phase_bases=(0, 0, 0), foul_probability=(0, 0, 0)))
        home, away = team("h"), team("a")
        before = deepcopy(home)
        result = engine.simulate_knockout(home, away, 42)
        self.assertTrue(result["extra_time"])
        self.assertEqual(result["duration"], 120)
        self.assertIn(result["winner_id"], {"h", "a"})
        self.assertNotEqual(result["shootout_score"]["h"], result["shootout_score"]["a"])
        self.assertEqual(result["score"], {"h": 0, "a": 0})
        self.assertEqual(home, before)
        self.assertTrue(all(p["minutes"] == 120 for p in match_player_summaries(result)))
        self.assertEqual(result, engine.simulate_knockout(home, away, 42))

    def test_regulation_engine_preserved_when_extending(self):
        for block in (5, 7):
            engine = MatchEngine(MatchConfig(block_minutes=block))
            normal = engine.simulate(team("h"), team("a"), 4)
            extended = engine.simulate(team("h"), team("a"), 4, minutes=120)
            self.assertEqual(normal["score"], extended["regulation_score"])
            self.assertEqual(normal["events"], [e for e in extended["events"] if e["minute"] <= 90])

    def test_five_season_balance_with_gate_and_prizes(self):
        config = EconomyConfig()
        balances = [config.STARTING_CASH] * 20
        stadium = {"ticket_price": 2000, "capacity": 10000}
        for season in range(5):
            for index in range(20):
                club = {
                    "supporters": round(1000 * 1.05**season),
                    "fan_satisfaction": 50,
                    "reputation": 10 + season,
                }
                gate = FanBaseService.attendance(club, stadium) * stadium["ticket_price"] * 19
                position = (index + season * 4) % 20 + 1
                balances[index] += (
                    12 * (config.fixed_revenue - config.payroll_target)
                    + gate
                    + config.prize(position, 0)
                )
            # Cup phase prizes and champion award are a finite pool, not recurring grants.
            balances[season] += 19 * 50000 + 1000000
        self.assertGreater(min(balances), config.STARTING_CASH)
        self.assertLess(max(balances), config.STARTING_CASH * 6)
        self.assertLess(sum(balances), 20 * config.STARTING_CASH * 5)
