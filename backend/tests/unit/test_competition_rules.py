import unittest
from collections import Counter
from datetime import UTC, datetime
from random import Random
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.config.game import GameConfig
from app.config.names import club_name
from app.services.competition import CompetitionService, division_name, movement, round_robin
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
        self.assertTrue(all(2 <= d < 15 for d in offsets[:20]))
        self.assertTrue(all(17 <= d < 30 for d in offsets[20:]))
        days = Counter(int(offset) for offset in offsets)
        self.assertTrue(all(count == 2 for count in days.values()))
        self.assertTrue(all(b - a == 0.5 for a, b in zip(offsets[:19], offsets[1:20])))
        self.assertTrue(all(b - a == 0.5 for a, b in zip(offsets[20:-1], offsets[21:])))
        custom = (2,) * 19 + (17,) * 19
        self.assertEqual(GameConfig(ROUND_OFFSETS_DAYS=custom).round_offsets(), custom)
        with self.assertRaises(ValueError):
            GameConfig(ROUND_OFFSETS_DAYS=(15,) * 38)
        with self.assertRaises(ValueError):
            GameConfig(ROUND_OFFSETS_DAYS=(float("nan"),) * 38)

    def test_generated_fixtures_and_calendar_have_two_matches_per_club_per_day(self):
        config = GameConfig()
        season = {
            "_id": "season",
            "starts_at": datetime(2026, 10, 1, tzinfo=UTC),
            "config": config.snapshot(),
        }
        division = {"_id": "division", "name": "A"}
        slots = [{"_id": i, "club_id": i} for i in range(20)]
        repo = Mock()
        with patch.object(CompetitionService, "refresh_positions"):
            CompetitionService.schedule(repo, season, division, slots)
        fixtures = repo.insert_many.call_args_list[0].args[1]
        events = repo.insert_many.call_args_list[1].args[1]
        counts = Counter()
        for match in fixtures:
            for side in ("home_club_id", "away_club_id"):
                counts[(match[side], match["date"].date())] += 1
        self.assertEqual(len(fixtures), 380)
        self.assertTrue(all(count == 2 for count in counts.values()))
        match_dates = {match["_id"]: match["date"] for match in fixtures}
        self.assertEqual(len(events), 760)
        self.assertTrue(
            all(event["date"] == match_dates[event["reference_id"]] for event in events)
        )

    def test_bot_name_combinations_are_varied_and_reproducible(self):
        names = {club_name(Random(seed)) for seed in range(30)}
        self.assertGreater(len(names), 20)
        self.assertTrue(all(not name.startswith("Bot ") for name in names))
        self.assertEqual(club_name(Random("club")), club_name(Random("club")))

    def test_table_card_totals_follow_slots_including_replaced_bots(self):
        repo = Mock()
        repo.owned.return_value = {"_id": "club"}
        repo.find.side_effect = [
            {"_id": "season"},
            {"division_id": "division"},
            {"_id": "division"},
        ]
        repo.many.side_effect = [
            [{"_id": "slot", "club_id": "club"}],
            [
                {
                    "home_slot_id": "slot",
                    "away_slot_id": "other-slot",
                    "home_club_id": "previous-bot",
                    "away_club_id": "other",
                    "result": {"statistics": {"previous-bot": {"yellow_cards": 3, "red_cards": 1}}},
                },
                {
                    "home_slot_id": "slot",
                    "away_slot_id": "other-slot",
                    "home_club_id": "club",
                    "away_club_id": "other",
                    "result": {"statistics": {"club": {"yellow_cards": 2, "red_cards": 0}}},
                },
            ],
        ]
        table = CompetitionService(repo).table(SimpleNamespace(id="user"))
        self.assertEqual(table["standings"][0]["yellow_cards"], 5)
        self.assertEqual(table["standings"][0]["red_cards"], 1)

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
            Counter(p["position"] for p in squad), {"GK": 3, "FB": 4, "CB": 4, "MID": 8, "ATT": 6}
        )
        self.assertTrue(all(p["strength"] <= 30 for p in squad))
        youth = generator.youth("club", "BR")
        self.assertEqual(len(youth), 3)
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
