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
            self.assertAlmostEqual((second - first) * 1440, 60)
        custom = (2,) * 19 + (17,) * 19
        self.assertEqual(GameConfig(ROUND_OFFSETS_DAYS=custom).round_offsets(), custom)
        with self.assertRaises(ValueError):
            GameConfig(ROUND_OFFSETS_DAYS=(15,) * 38)
        with self.assertRaises(ValueError):
            GameConfig(ROUND_OFFSETS_DAYS=(float("nan"),) * 38)

    def test_generated_fixtures_and_calendar_have_hourly_intervals(self):
        config = GameConfig()
        season = {
            "_id": "season",
            "starts_at": datetime(2026, 10, 1, tzinfo=UTC),
            "config": config.snapshot(),
        }
        division = {"_id": "division", "name": "A"}
        slots = [{"_id": i, "club_id": i} for i in range(20)]
        repo = Mock()
        repo.rules.return_value = {}
        with patch.object(CompetitionService, "refresh_positions"):
            CompetitionService.schedule(repo, season, division, slots)
        fixtures = repo.insert_many.call_args_list[0].args[1]
        events = repo.insert_many.call_args_list[1].args[1]
        counts = Counter()
        for match in fixtures:
            for side in ("home_club_id", "away_club_id"):
                counts[(match[side], match["date"].date())] += 1
        self.assertEqual(len(fixtures), 380)
        self.assertTrue(all(count <= 24 for count in counts.values()))
        dates = sorted({match["date"] for match in fixtures})
        self.assertTrue(all((b - a).total_seconds() == 3600 for a, b in zip(dates, dates[1:])))
        match_dates = {match["_id"]: match["date"] for match in fixtures}
        self.assertEqual(len(events), 760)
        self.assertTrue(
            all(event["date"] == match_dates[event["reference_id"]] for event in events)
        )

    def test_existing_league_is_rescheduled_once_without_touching_completed_matches(self):
        repo = Mock()
        repo.rules.return_value = {}
        season = {"_id": "season", "starts_at": datetime(2026, 10, 1, tzinfo=UTC)}
        repo.find.return_value = season
        pending = [{"_id": "a", "round": 3}, {"_id": "b", "round": 3}, {"_id": "c", "round": 4}]
        repo.many.side_effect = lambda collection, query, **kwargs: (
            pending if collection == "matches" else []
        )
        now = datetime(2026, 10, 11, tzinfo=UTC)
        with patch("app.services.competition.utcnow", return_value=now):
            CompetitionService.update_league_interval(repo)
        query = repo.many.call_args.args[1]
        self.assertEqual(query["status"], "scheduled")
        self.assertEqual(query["division_id"], {"$exists": True})
        operations = repo.database.matches.bulk_write.call_args.args[0]
        dates = [operation._doc["$set"]["date"] for operation in operations]
        self.assertEqual(operations[0]._filter["_id"]["$in"], ["a", "b"])
        self.assertEqual((dates[0] - now).total_seconds(), 3600)
        self.assertEqual((dates[1] - dates[0]).total_seconds(), 3600)
        repo.database.calendar_events.bulk_write.assert_called_once()
        saved = repo.update.call_args.args[2]["$set"]
        self.assertEqual(saved["config.MATCH_INTERVAL_MINUTES"], 60)
        self.assertEqual(saved["config.ROUND_OFFSETS_DAYS"], [])
        repo.reset_mock()
        repo.find.return_value = {
            **season,
            "league_interval_minutes": 10,
            "league_schedule_revision": 4,
            "league_games_per_day": 24,
        }
        CompetitionService.update_league_interval(repo)
        repo.many.assert_not_called()

    def test_old_saved_offsets_cannot_restore_two_matches_per_day(self):
        repo = Mock()
        repo.rules.return_value = {}
        repo.rules.return_value = {
            "MATCH_INTERVAL_MINUTES": 720,
            "ROUND_OFFSETS_DAYS": [2 + i / 2 for i in range(20)] + [17 + i / 2 for i in range(18)],
        }
        season = CompetitionService.create_season(repo, datetime(2026, 10, 11, tzinfo=UTC))
        offsets = GameConfig(**season["config"]).round_offsets()
        self.assertEqual(season["league_schedule_revision"], 4)
        for first, second in zip(offsets, offsets[1:]):
            self.assertAlmostEqual((second - first) * 1440, 60)

    def test_periodic_processing_applies_pending_calendar_migration(self):
        repo = Mock()
        repo.rules.return_value = {}
        now = datetime(2026, 10, 11, tzinfo=UTC)
        old = {"_id": "season", "ends_at": datetime(2026, 11, 1, tzinfo=UTC)}
        updated = {**old, "league_schedule_revision": 4, "league_games_per_day": 24}
        with (
            patch.object(CompetitionService, "current", side_effect=[old, updated]),
            patch.object(CompetitionService, "play_due") as play,
        ):
            CompetitionService(repo).process_due(now)
        repo.transaction.assert_called_once_with(CompetitionService.update_league_interval)
        play.assert_called_once_with(updated, now)

    def test_calendar_read_leaves_schedule_repairs_to_background(self):
        repo = Mock()
        repo.rules.return_value = {}
        repo.owned.return_value = {"_id": "club"}
        repo.find.return_value = {"_id": "season"}
        repo.many.return_value = []
        CalendarService(repo).get(
            SimpleNamespace(id="user"), SimpleNamespace(type=None, start=None, end=None)
        )
        repo.transaction.assert_not_called()
        self.assertEqual(repo.many.call_args_list[0].args[0], "calendar_events")
        self.assertEqual(repo.many.call_args_list[0].args[1]["club_id"], "club")
        repo.reset_mock()
        repo.find.return_value = {
            "_id": "season",
            "league_schedule_revision": 4,
            "league_games_per_day": 24,
        }
        CalendarService(repo).get(
            SimpleNamespace(id="user"), SimpleNamespace(type=None, start=None, end=None)
        )
        repo.transaction.assert_not_called()

    def test_calendar_returns_actual_status_and_score_from_match_documents(self):
        repo = Mock()
        repo.rules.return_value = {}
        repo.owned.return_value = {"_id": "club"}
        repo.find.return_value = {"league_schedule_revision": 4, "league_games_per_day": 24}
        events = []
        repo.many.side_effect = lambda collection, *args, **kwargs: (
            events
            if collection == "calendar_events"
            else [
                {
                    "_id": "match",
                    "date": "past",
                    "status": "completed",
                    "home_goals": 2,
                    "away_goals": 1,
                }
            ]
            if collection == "matches"
            else []
        )
        result = CalendarService(repo).get(
            SimpleNamespace(id="user"), SimpleNamespace(type=None, start=None, end=None)
        )
        self.assertEqual(result[0]["reference_id"], "match")
        self.assertEqual(result[0]["status"], "completed")
        self.assertEqual(result[0]["home_goals"], 2)
        self.assertEqual(repo.many.call_count, 5)

    def test_one_failed_match_does_not_block_other_due_matches(self):
        repo = Mock()
        repo.rules.return_value = {}
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

    def test_daily_frequency_is_configurable_and_skips_transfer_window(self):
        config = GameConfig(MATCHES_PER_DAY=2)
        offsets = config.round_offsets()
        self.assertEqual(config.MATCH_INTERVAL_MINUTES, 720)
        self.assertEqual(len(offsets), 38)
        self.assertTrue(all(not 15 <= day < 17 for day in offsets))
        self.assertTrue(all(day < 30 for day in offsets))
        for value in (0, 1441, True, 2.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                GameConfig(MATCHES_PER_DAY=value)
        repo = Mock()
        repo.rules.return_value = {"MATCHES_PER_DAY": 12}
        season = {"league_schedule_revision": 4, "league_games_per_day": 24}
        self.assertTrue(CompetitionService.needs_schedule_update(repo, season))
        season["league_games_per_day"] = 12
        self.assertFalse(CompetitionService.needs_schedule_update(repo, season))

    def test_october_eighth_season_catches_up_after_only_three_completed_rounds(self):
        from datetime import timedelta

        config = GameConfig()
        season = {
            "_id": "season",
            "starts_at": datetime(2026, 10, 8, tzinfo=UTC),
            "config": config.snapshot(),
        }
        repo = Mock()
        with patch.object(CompetitionService, "refresh_positions"):
            CompetitionService.schedule(
                repo,
                season,
                {"_id": "division", "name": "A"},
                [{"_id": i, "club_id": i} for i in range(20)],
            )
        matches = repo.insert_many.call_args_list[0].args[1]
        for match in matches[:30]:
            match["status"] = "completed"
        for match in matches[30:]:
            match["date"] = datetime(2026, 10, 15, 0, 16, 23, tzinfo=UTC) + timedelta(
                hours=match["round"] - 4
            )
        now = datetime(2026, 10, 19, tzinfo=UTC)
        future = {**matches[-1], "_id": "future", "date": now + timedelta(hours=1)}
        matches.append(future)

        def many(collection, query, **kwargs):
            if collection != "matches":
                return []
            return [
                match
                for match in matches
                if match["status"] == "scheduled"
                and match["date"] <= query["date"]["$lte"]
                and match["_id"] not in query["_id"]["$nin"]
            ][:1]

        def play(identity, when):
            next(match for match in matches if match["_id"] == identity)["status"] = "completed"

        repo.many.side_effect = many
        service = CompetitionService(repo)
        with (
            patch("app.services.live_match.busy_clubs", return_value=set()),
            patch.object(service, "play", side_effect=play) as played,
        ):
            for _ in range(35):
                self.assertEqual(service.play_due(season, now, max_matches=10), 10)
            self.assertEqual(played.call_count, 350)
            self.assertEqual(service.play_due(season, now, max_matches=10), 0)
            self.assertEqual(played.call_count, 350)
        self.assertEqual(future["status"], "scheduled")
        self.assertTrue(all(match["status"] == "completed" for match in matches[:380]))

    def test_bounded_processing_defers_season_finalization_until_next_batch(self):
        now = datetime(2026, 10, 19, tzinfo=UTC)
        service = CompetitionService(Mock())
        season = {"_id": "season", "ends_at": datetime(2026, 10, 18, tzinfo=UTC)}
        with (
            patch.object(service, "current", return_value=season),
            patch.object(service, "needs_schedule_update", return_value=False),
            patch.object(service, "play_due", return_value=10) as play,
            patch("app.services.competition.SeasonFinalizationService") as finalization,
        ):
            service.process_due(now, max_matches=10)
        play.assert_called_once_with(season, now, max_matches=10)
        finalization.assert_not_called()

    def test_missing_fixtures_after_round_seven_are_restored_without_replaying_results(self):
        from copy import deepcopy

        config = GameConfig()
        season = {
            "_id": "season",
            "starts_at": datetime(2026, 10, 1, tzinfo=UTC),
            "config": config.snapshot(),
        }
        division = {"_id": "division", "name": "A"}
        slots = [{"_id": i, "club_id": i} for i in range(20)]
        generated = Mock()
        with patch.object(CompetitionService, "refresh_positions"):
            CompetitionService.schedule(generated, season, division, slots)
        matches = generated.insert_many.call_args_list[0].args[1][:70]
        for match in matches:
            match.update(status="completed", home_goals=2, away_goals=1)
        previous = deepcopy(matches)
        repo = Mock()
        repo.find.return_value = season
        repo.rules.return_value = {}

        def many(collection, query, **kwargs):
            if collection == "divisions":
                return [division]
            if collection == "season_clubs":
                return slots
            return (
                [m for m in matches if m["status"] == "scheduled"]
                if query.get("status")
                else matches
            )

        repo.many.side_effect = many
        repo.insert_many.side_effect = lambda collection, rows: (
            matches.extend(rows) if collection == "matches" else None
        )
        now = datetime(2026, 10, 4, tzinfo=UTC)
        with (
            patch("app.services.competition.utcnow", return_value=now),
            patch.object(CompetitionService, "refresh_positions"),
        ):
            CompetitionService.update_league_interval(repo)
        self.assertEqual(len(matches), 380)
        self.assertEqual(matches[:70], previous)
        self.assertEqual(len({(m["home_slot_id"], m["away_slot_id"]) for m in matches}), 380)
        operations = repo.database.matches.bulk_write.call_args.args[0]
        self.assertEqual(sum(len(operation._filter["_id"]["$in"]) for operation in operations), 310)
        self.assertTrue(all(operation._filter["status"] == "scheduled" for operation in operations))
        dates = sorted(operation._doc["$set"]["date"] for operation in operations)
        self.assertLessEqual(dates[0], now)
        self.assertEqual(len(dates), 31)
        self.assertTrue(all((b - a).total_seconds() == 3600 for a, b in zip(dates, dates[1:])))

    def test_bot_name_combinations_are_varied_and_reproducible(self):
        names = {club_name(Random(seed)) for seed in range(30)}
        self.assertGreater(len(names), 20)
        self.assertTrue(all(not name.startswith("Bot ") for name in names))
        self.assertEqual(club_name(Random("club")), club_name(Random("club")))

    def test_table_card_totals_follow_slots_including_replaced_bots(self):
        repo = Mock()
        repo.rules.return_value = {}
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
