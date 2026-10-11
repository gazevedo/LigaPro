import unittest
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from bson import ObjectId

from app.config.game import GameConfig
from app.models.game import DEFAULT_RULES, utcnow
from app.services.physical_condition import PhysicalConditionService


class CardDisciplineTests(unittest.TestCase):
    def setUp(self):
        self.home, self.away, self.identity = ObjectId(), ObjectId(), ObjectId()
        self.now = utcnow()
        self.player = {
            "_id": self.identity,
            "current_club_id": self.home,
            "name": "Jogador",
            "age": 24,
            "status": "available",
            "energy": 100,
        }
        self.repo = Mock()
        self.repo.session = None
        self.repo.rules.return_value = DEFAULT_RULES
        self.repo.find.return_value = {}
        self.repo.many.side_effect = lambda *args, **kwargs: [deepcopy(self.player)]
        self.repo.database = SimpleNamespace(players=SimpleNamespace(bulk_write=self.apply))
        self.news = patch("app.services.news.NewsService.publish").start()
        self.addCleanup(patch.stopall)
        self.service = PhysicalConditionService()

    def apply(self, operations, **kwargs):
        for operation in operations:
            self.assertEqual(operation._filter["_id"], self.identity)
            self.player.update(operation._doc["$set"])

    def play(self, yellows=0, reds=0, *, participate=True, second_yellow=False, discipline=True):
        match = {
            "_id": ObjectId(),
            "date": self.now,
            "home_club_id": self.home,
            "away_club_id": self.away,
        }
        result = {
            "snapshot": {
                "home": {"id": str(self.home), "marking": "light", "style": "balanced"},
                "away": {"id": str(self.away), "marking": "light", "style": "balanced"},
            },
            "events": [
                {"type": "red_card", "reason": "second_yellow", "player_id": str(self.identity)}
            ]
            if second_yellow
            else [],
        }
        rows = (
            [
                {
                    "player_id": str(self.identity),
                    "club_id": str(self.home),
                    "minutes": 90,
                    "yellow_cards": yellows,
                    "red_cards": reds,
                }
            ]
            if participate
            else []
        )
        self.service.after_match(self.repo, match, result, rows, discipline=discipline)

    def test_three_accumulated_yellows_suspend_one_match_and_reset_the_counter(self):
        for cards in (1, 0, 1):
            self.play(cards)
            self.assertEqual(self.player["status"], "available")
        self.play(1)
        self.assertEqual(self.player["yellow_cards_accumulated"], 0)
        self.assertEqual(self.player["suspension_matches_remaining"], 1)
        self.assertEqual(self.player["status"], "suspended")
        self.assertTrue(self.player["discipline_yellow_suspension"])
        self.assertEqual(self.news.call_count, 1)

    def test_time_does_not_serve_a_ban_but_the_next_completed_match_does(self):
        self.play(reds=1)
        self.service.prepare(self.repo, self.home, self.now + timedelta(days=30))
        self.assertEqual(self.player["status"], "suspended")
        self.assertEqual(self.player["suspension_matches_remaining"], 1)
        # Includes W.O.: no player summaries are required to serve a suspension.
        self.play(participate=False)
        self.assertEqual(self.player["status"], "available")
        self.assertEqual(self.player["suspension_matches_remaining"], 0)
        self.assertFalse(self.player["discipline_red_card"])

    def test_second_yellow_causes_one_ban_without_adding_to_accumulated_yellows(self):
        self.player["yellow_cards_accumulated"] = 2
        self.play(yellows=2, reds=1, second_yellow=True)
        self.assertEqual(self.player["yellow_cards_accumulated"], 2)
        self.assertEqual(self.player["suspension_matches_remaining"], 1)
        self.assertTrue(self.player["discipline_red_card"])

    def test_injury_still_blocks_the_player_after_serving_the_ban(self):
        self.play(reds=1)
        self.player.update(status="injured", injury_return_at=self.now + timedelta(days=5))
        self.play(participate=False)
        self.assertEqual(self.player["status"], "injured")
        self.assertEqual(self.player["suspension_matches_remaining"], 0)

    def test_friendlies_neither_accumulate_yellows_nor_serve_a_ban(self):
        self.play(yellows=1, discipline=False)
        self.assertNotIn("yellow_cards_accumulated", self.player)
        self.play(reds=1)
        self.play(participate=False, discipline=False)
        self.assertEqual(self.player["suspension_matches_remaining"], 1)

    def test_card_rules_require_positive_integer_values(self):
        self.assertEqual(GameConfig().YELLOW_CARD_SUSPENSION_THRESHOLD, 3)
        self.assertEqual(GameConfig().CARD_SUSPENSION_MATCHES, 1)
        with self.assertRaises(ValueError):
            GameConfig(YELLOW_CARD_SUSPENSION_THRESHOLD=0)
        with self.assertRaises(ValueError):
            GameConfig(CARD_SUSPENSION_MATCHES=1.5)
