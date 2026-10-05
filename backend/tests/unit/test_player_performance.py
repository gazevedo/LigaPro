import unittest
from copy import deepcopy
from statistics import pvariance

from test_match_engine import team

from app.config.game import GameConfig
from app.config.team_performance import ChemistryConfig, MoraleConfig
from app.models.player import market_value, player_public
from app.services.bot_market import BotMarketService
from app.services.match_engine import (
    MatchConfig,
    MatchEngine,
    MatchPlayer,
    PlayerEffectiveStrengthCalculator,
)
from app.services.player_development import PlayerGeneratorService
from app.services.player_ratings import PlayerRatingService
from app.services.player_statistics import match_player_summaries


def sample_result():
    home, away = team("home"), team("away")
    home.reserves = [MatchPlayer("home-bench", "ATT", "ATT")]
    result = MatchEngine().simulate(home, away, 5)
    result["score"] = {"home": 3, "away": 1}

    def event(minute, kind, player=None, club="home", **extra):
        return {"minute": minute, "type": kind, "player_id": player, "team_id": club, **extra}

    result["events"] = [
        event(15, "goal", "home-9"),
        event(30, "goal", "away-9", "away"),
        event(40, "shot_saved", "home-9", goalkeeper_id="away-0"),
        event(45, "yellow_card", "home-1"),
        event(50, "shot_off_target", "home-10", penalty=True),
        event(60, "substitution", out_player_id="home-10", in_player_id="home-bench"),
        event(70, "goal", "home-bench", penalty=True),
        event(75, "goal", "home-9"),
        event(80, "yellow_card", "home-1"),
        event(80, "red_card", "home-1", reason="second_yellow"),
        event(85, "duel", "home-9", attacker_id="home-9", defender_id="away-1", winner_id="away-1"),
        event(90, "shot_saved", "away-9", "away", goalkeeper_id="home-0"),
    ]
    return result


class PlayerPerformanceTests(unittest.TestCase):
    def test_generated_potential_and_youth_distribution(self):
        adults, youths = [], []
        for youth, group in ((False, adults), (True, youths)):
            generator = PlayerGeneratorService(seed=42)
            for _ in range(2000):
                player = generator.player("club", "BR", youth=youth)
                self.assertTrue(player["strength"] <= player["potential"] <= 100)
                group.append(player["potential"])
        self.assertGreater(sum(x >= 80 for x in youths), sum(x >= 80 for x in adults) * 3)
        self.assertGreater(pvariance(youths), pvariance(adults))
        player = PlayerGeneratorService(GameConfig(MAX_PLAYER_LEVEL=20), 4).player(
            "club", "BR", youth=True
        )
        self.assertEqual(player["strength"], 20)
        self.assertEqual(player["potential"], 20)

    def test_potential_is_internal_and_affects_market_and_bot_decisions(self):
        common = {"strength": 50, "potential": 60, "age": 18, "status": "active"}
        promise = {**common, "potential": 90}
        self.assertGreater(market_value(50, 90, 18), market_value(50, 60, 18))
        self.assertNotIn("potential", player_public(promise))
        self.assertTrue(player_public(promise)["can_train"])
        self.assertFalse(player_public({**promise, "strength": 90})["can_train"])
        self.assertGreater(
            BotMarketService.score({"strength": 50, "potential": 100}),
            BotMarketService.score({"strength": 60, "potential": 60}),
        )

    def test_bounded_morale_and_chemistry_modifiers(self):
        player = MatchPlayer("p", "MID", "MID", strength=70)
        calculator = PlayerEffectiveStrengthCalculator(MatchConfig(), "classic")
        neutral = calculator.calculate(player, "passing")
        for value in range(101):
            player.morale = value
            ratio = calculator.calculate(player, "passing") / neutral
            self.assertTrue(0.94 - 1e-9 <= ratio <= 1.04 + 1e-9)
            self.assertTrue(0.92 <= ChemistryConfig().modifier(value) <= 1.04)
        self.assertEqual(
            [MoraleConfig().modifier(n) for n in (0, 21, 41, 61, 81)], [0.94, 0.97, 1, 1.02, 1.04]
        )
        engine = MatchEngine()
        players = team("h").lineup
        normal = engine.sectors.contribution(players, "passing", chemistry=50)
        self.assertAlmostEqual(
            engine.sectors.contribution(players, "passing", chemistry=0) / normal, 0.92
        )
        self.assertAlmostEqual(
            engine.sectors.contribution(players, "passing", chemistry=100) / normal, 1.04
        )
        with self.assertRaises(ValueError):
            MoraleConfig(factors=(1, 1, 1, 1, 1.10))
        with self.assertRaises(ValueError):
            ChemistryConfig(factors=(0.8, 1, 1, 1, 1.04))

    def test_substitution_cards_goals_penalties_and_minutes(self):
        result = sample_result()
        rows = {row["player_id"]: row for row in match_player_summaries(result)}
        self.assertEqual(rows["home-10"]["minutes"], 60)
        self.assertEqual(rows["home-bench"]["minutes"], 30)
        self.assertEqual(rows["home-bench"]["starts"], 0)
        self.assertEqual(rows["home-1"]["minutes"], 80)
        self.assertEqual(rows["home-1"]["yellow_cards"], 2)
        self.assertEqual(rows["home-1"]["red_cards"], 1)
        self.assertEqual(rows["home-9"]["goals"], 2)
        self.assertEqual(rows["home-bench"]["penalties_scored"], 1)
        self.assertEqual(rows["home-10"]["penalties_missed"], 1)
        self.assertEqual(rows["away-0"]["saves"], 1)
        self.assertEqual(rows["home-0"]["saves"], 1)
        self.assertEqual(sum(r["minutes"] for r in rows.values() if r["club_id"] == "home"), 980)
        self.assertTrue(all(0 < r["minutes"] <= 90 for r in rows.values()))
        self.assertEqual(rows["away-1"]["defensive_actions"], 1)
        self.assertEqual(sum(r["goals"] for r in rows.values()), 4)

    def test_zero_minute_substitutions_and_unused_bench_do_not_count_matches(self):
        result = sample_result()
        result["events"] = [
            {
                "minute": 0,
                "type": "substitution",
                "team_id": "home",
                "out_player_id": "home-10",
                "in_player_id": "home-bench",
            }
        ]
        rows = {r["player_id"]: r for r in match_player_summaries(result)}
        self.assertNotIn("home-10", rows)
        self.assertEqual(rows["home-bench"]["starts"], 1)
        self.assertEqual(rows["home-bench"]["minutes"], 90)
        result["events"] = []
        self.assertNotIn("home-bench", {r["player_id"] for r in match_player_summaries(result)})
        self.assertEqual(match_player_summaries({"walkover": True}), [])

    def test_ratings_goal_red_limits_and_keeper_can_play_well_in_defeat(self):
        result = sample_result()
        row = next(r for r in match_player_summaries(result) if r["player_id"] == "home-0")
        base = {**row, "goals": 0, "shots": 0, "saves": 0, "goals_conceded": 0}
        normal = PlayerRatingService.calculate(base, result)
        self.assertGreater(
            PlayerRatingService.calculate({**base, "goals": 1, "shots": 1}, result), normal
        )
        self.assertLess(PlayerRatingService.calculate({**base, "red_cards": 1}, result), normal)
        self.assertEqual(PlayerRatingService.calculate({**base, "goals": 30}, result), 10)
        self.assertEqual(PlayerRatingService.calculate({**base, "red_cards": 30}, result), 5)
        losing = deepcopy(result)
        losing["score"] = {"home": 0, "away": 2}
        self.assertGreater(
            PlayerRatingService.calculate({**base, "saves": 14, "goals_conceded": 2}, losing), 8
        )
        for summary in match_player_summaries(result):
            self.assertTrue(5 <= PlayerRatingService.calculate(summary, result) <= 10)


if __name__ == "__main__":
    unittest.main()
