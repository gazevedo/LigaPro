import unittest
from collections import Counter
from datetime import UTC, datetime
from random import Random
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.config.game import GameConfig
from app.config.names import club_name
from app.services.competition import CompetitionService, division_name, movement, round_robin
from app.services.game import CalendarService
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
        self.assertEqual(offsets[0], 2)
        for first, second in zip(offsets, offsets[1:]):
            self.assertAlmostEqual((second - first) * 1440, 10)
        custom = (2,) * 19 + (17,) * 19
        self.assertEqual(GameConfig(ROUND_OFFSETS_DAYS=custom).round_offsets(), custom)
        with self.assertRaises(ValueError):
            GameConfig(ROUND_OFFSETS_DAYS=(15,) * 38)
        with self.assertRaises(ValueError):
            GameConfig(ROUND_OFFSETS_DAYS=(float("nan"),) * 38)

    def test_generated_fixtures_and_calendar_have_ten_minute_intervals(self):
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
        self.assertTrue(all(count == 38 for count in counts.values()))
        dates = sorted({match["date"] for match in fixtures})
        self.assertTrue(all((b - a).total_seconds() == 600 for a, b in zip(dates, dates[1:])))
        match_dates = {match["_id"]: match["date"] for match in fixtures}
        self.assertEqual(len(events), 760)
        self.assertTrue(
            all(event["date"] == match_dates[event["reference_id"]] for event in events)
        )

    def test_existing_league_is_rescheduled_once_without_touching_completed_matches(self):
        repo = Mock()
        season = {"_id": "season"}
        repo.find.return_value = season
        repo.many.return_value = [
            {"_id": "a", "round": 3},
            {"_id": "b", "round": 3},
            {"_id": "c", "round": 4},
        ]
        now = datetime(2026, 10, 11, tzinfo=UTC)
        with patch("app.services.competition.utcnow", return_value=now):
            CompetitionService.update_league_interval(repo)
        query = repo.many.call_args.args[1]
        self.assertEqual(query["status"], "scheduled")
        self.assertEqual(query["division_id"], {"$exists": True})
        dates = [
            call.args[2]["$set"]["date"]
            for call in repo.update.call_args_list
            if call.args[0] == "matches"
        ]
        self.assertEqual(dates[0], dates[1])
        self.assertEqual((dates[0] - now).total_seconds(), 600)
        self.assertEqual((dates[2] - dates[0]).total_seconds(), 600)
        saved = repo.update.call_args.args[2]["$set"]
        self.assertEqual(saved["config.MATCH_INTERVAL_MINUTES"], 10)
        self.assertEqual(saved["config.ROUND_OFFSETS_DAYS"], [])
        repo.reset_mock()
        repo.find.return_value = {
            **season,
            "league_interval_minutes": 10,
            "league_schedule_revision": 2,
        }
        CompetitionService.update_league_interval(repo)
        repo.many.assert_not_called()

    def test_old_saved_offsets_cannot_restore_two_matches_per_day(self):
        repo = Mock()
        repo.rules.return_value = {
            "MATCH_INTERVAL_MINUTES": 720,
            "ROUND_OFFSETS_DAYS": [2 + i / 2 for i in range(20)] + [17 + i / 2 for i in range(18)],
        }
        season = CompetitionService.create_season(repo, datetime(2026, 10, 11, tzinfo=UTC))
        offsets = GameConfig(**season["config"]).round_offsets()
        self.assertEqual(season["league_schedule_revision"], 2)
        for first, second in zip(offsets, offsets[1:]):
            self.assertAlmostEqual((second - first) * 1440, 10)

    def test_periodic_processing_applies_pending_calendar_migration(self):
        repo = Mock()
        now = datetime(2026, 10, 11, tzinfo=UTC)
        old = {"_id": "season", "ends_at": datetime(2026, 11, 1, tzinfo=UTC)}
        updated = {**old, "league_schedule_revision": 2}
        with (
            patch.object(CompetitionService, "current", side_effect=[old, updated]),
            patch.object(CompetitionService, "play_due") as play,
        ):
            CompetitionService(repo).process_due(now)
        repo.transaction.assert_called_once_with(CompetitionService.update_league_interval)
        play.assert_called_once_with(updated, now)

    def test_calendar_read_repairs_pending_schedule_before_reading_events(self):
        repo = Mock()
        repo.owned.return_value = {"_id": "club"}
        repo.find.return_value = {"_id": "season"}
        repo.many.return_value = []
        CalendarService(repo).get(
            SimpleNamespace(id="user"), SimpleNamespace(type=None, start=None, end=None)
        )
        repo.transaction.assert_called_once_with(CompetitionService.update_league_interval)
        repo.many.assert_called_once_with(
            "calendar_events", {"club_id": "club"}, limit=500, sort=[("date", 1)]
        )
        repo.reset_mock()
        repo.find.return_value = {"_id": "season", "league_schedule_revision": 2}
        CalendarService(repo).get(
            SimpleNamespace(id="user"), SimpleNamespace(type=None, start=None, end=None)
        )
        repo.transaction.assert_not_called()

    def test_calendar_returns_actual_status_and_score_from_match_documents(self):
        repo = Mock()
        repo.owned.return_value = {"_id": "club"}
        repo.find.return_value = {"league_schedule_revision": 2}
        events = [{"_id": "event", "reference_id": "match", "date": "past", "status": "scheduled"}]
        repo.many.side_effect = lambda collection, *args, **kwargs: (
            events
            if collection == "calendar_events"
            else [{"_id": "match", "status": "completed", "home_goals": 2, "away_goals": 1}]
            if collection == "matches"
            else []
        )
        result = CalendarService(repo).get(
            SimpleNamespace(id="user"), SimpleNamespace(type=None, start=None, end=None)
        )
        self.assertEqual(result[0]["id"], "event")
        self.assertEqual(result[0]["status"], "completed")
        self.assertEqual(result[0]["home_goals"], 2)
        self.assertEqual(repo.many.call_count, 4)

    def test_one_failed_match_does_not_block_other_due_matches(self):
        repo = Mock()
        now = datetime(2026, 10, 11, tzinfo=UTC)
        repo.many.side_effect = [
            [{"_id": "broken", "date": now}],
            [],
            [],
            [{"_id": "next", "date": now}],
            [],
            [],
            [],
            [],
            [],
        ]
        service = CompetitionService(repo)
        with (
            patch("app.services.live_match.busy_clubs", return_value=set()),
            patch.object(service, "play", side_effect=[RuntimeError("broken"), {}]) as play,
        ):
            service.play_due({"_id": "season"}, now)
        self.assertEqual(play.call_count, 2)
        self.assertIn("broken", repo.many.call_args_list[3].args[1]["_id"]["$nin"])

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
