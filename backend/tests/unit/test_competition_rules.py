import unittest
from collections import Counter

from app.config.game import GameConfig
from app.services.competition import division_name, movement, round_robin
from app.services.player_development import PlayerAgingService, PlayerGeneratorService


class CompetitionRulesTests(unittest.TestCase):
    def test_double_round_robin(self):
        rounds = round_robin(list(range(20)))
        self.assertEqual(len(rounds), 38)
        pair_counts = Counter()
        for pairs in rounds:
            self.assertEqual(len(pairs), 10)
            self.assertEqual({p for pair in pairs for p in pair}, set(range(20)))
            pair_counts.update(pairs)
        self.assertEqual(len(pair_counts), 380)
        self.assertTrue(all(count == 1 for count in pair_counts.values()))

    def test_calendar_windows_and_custom_multiple_rounds_per_day(self):
        config = GameConfig()
        offsets = config.round_offsets()
        self.assertEqual(len(offsets), 38)
        self.assertTrue(all(2 <= d < 15 for d in offsets[:19]))
        self.assertTrue(all(17 <= d < 30 for d in offsets[19:]))
        custom = (2,) * 19 + (17,) * 19
        self.assertEqual(GameConfig(ROUND_OFFSETS_DAYS=custom).round_offsets(), custom)
        with self.assertRaises(ValueError):
            GameConfig(ROUND_OFFSETS_DAYS=(15,) * 38)
        with self.assertRaises(ValueError):
            GameConfig(ROUND_OFFSETS_DAYS=(float("nan"),) * 38)

    def test_unlimited_series_and_three_division_movements(self):
        self.assertEqual([division_name(i) for i in (0, 25, 26, 701)], ["A", "Z", "AA", "ZZ"])
        tables = {
            tier: [
                {
                    "_id": f"{tier}-{i:02}",
                    "club_id": f"{tier}-{i:02}",
                    "points": 100 - i,
                    "goal_difference": 0,
                    "goals_for": 0,
                    "wins": 0,
                }
                for i in range(20)
            ]
            for tier in range(3)
        }
        destinations = movement(tables, GameConfig())
        self.assertEqual(Counter(destinations.values()), {0: 20, 1: 20, 2: 20})
        self.assertEqual(sum(destinations[f"0-{i:02}"] == 1 for i in range(20)), 4)
        self.assertEqual(sum(destinations[f"1-{i:02}"] == 0 for i in range(20)), 4)
        self.assertEqual(sum(destinations[f"1-{i:02}"] == 2 for i in range(20)), 4)
        self.assertEqual(sum(destinations[f"2-{i:02}"] == 1 for i in range(20)), 4)

    def test_generator_config_and_age_probabilities(self):
        generator = PlayerGeneratorService(GameConfig(MAX_PLAYER_LEVEL=30), seed=1)
        squad = generator.squad("club", "BR")
        self.assertEqual(
            Counter(p["position"] for p in squad), {"GK": 3, "DEF": 8, "MID": 8, "ATT": 6}
        )
        self.assertTrue(all(p["strength"] <= 30 for p in squad))
        youth = generator.youth("club", "BR")
        self.assertEqual(len(youth), 2)
        self.assertTrue(all(14 <= p["age"] <= 17 for p in youth))
        config = GameConfig()
        self.assertEqual(PlayerAgingService.probability(34, config.DECLINE_PROBABILITIES), 0)
        self.assertEqual(PlayerAgingService.probability(100, config.RETIREMENT_PROBABILITIES), 0.5)
        for invalid in (
            {"INITIAL_SQUAD_SIZE": 24},
            {"PROMOTION_COUNT": 3},
            {"BOT_REPLACEMENT_STRATEGY": "unknown"},
            {"YOUTH_PLAYERS_PER_SEASON": 1.5},
        ):
            with self.assertRaises(ValueError):
                GameConfig(**invalid)


if __name__ == "__main__":
    unittest.main()
