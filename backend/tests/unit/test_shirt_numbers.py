import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.player import SHIRT_NUMBERS
from app.schemas.game import ShirtNumberInput
from app.services.game import SquadService
from app.services.player_development import PlayerGeneratorService


class ShirtNumberTests(unittest.TestCase):
    def setUp(self):
        self.club = ObjectId()
        self.player = {
            "_id": ObjectId(),
            "current_club_id": self.club,
            "position": "MID",
            "shirt_number": 8,
        }
        self.repo = Mock()
        self.repo.owned.return_value = {"_id": self.club}
        self.repo.document.return_value = self.player
        self.repo.find.return_value = None
        self.repo.transaction.side_effect = lambda callback: callback(self.repo)
        self.repo.update.side_effect = lambda collection, query, update: (
            {**self.player, **update.get("$set", {})} if collection == "players" else {}
        )
        self.user = SimpleNamespace(id=str(ObjectId()))

    def test_initial_squad_has_25_distinct_shirt_numbers(self):
        players = PlayerGeneratorService(seed=123).squad(self.club, "BR")
        self.assertEqual({p["shirt_number"] for p in players}, set(range(1, 26)))

    def test_save_locks_club_and_excludes_player_own_number(self):
        result = SquadService(self.repo).shirt_number(self.user, str(self.player["_id"]), 8)
        self.assertEqual(result["shirt_number"], 8)
        calls = self.repo.update.call_args_list
        self.assertEqual(calls[0].args[0], "clubs")
        self.assertEqual(calls[-1].args[0], "players")
        conflict_query = self.repo.find.call_args.args[1]
        self.assertEqual(conflict_query["current_club_id"], self.club)
        self.assertEqual(conflict_query["_id"], {"$ne": self.player["_id"]})

    def test_duplicate_number_is_rejected_without_changing_player(self):
        self.repo.find.return_value = {"_id": ObjectId(), "shirt_number": 9}
        with self.assertRaises(HTTPException) as raised:
            SquadService(self.repo).shirt_number(self.user, str(self.player["_id"]), 9)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertFalse(any(call.args[0] == "players" for call in self.repo.update.call_args_list))

    def test_other_club_player_cannot_be_edited(self):
        self.repo.document.return_value = {**self.player, "current_club_id": ObjectId()}
        with self.assertRaises(HTTPException) as raised:
            SquadService(self.repo).shirt_number(self.user, str(self.player["_id"]), 9)
        self.assertEqual(raised.exception.status_code, 403)

    def test_custom_numbers_are_preserved_while_automatic_numbers_use_position(self):
        players = [
            {"_id": ObjectId(), "shirt_number": 1, "shirt_number_custom": True},
            {"_id": ObjectId(), "shirt_number": 1, "shirt_number_custom": True},
            {"_id": ObjectId(), "position": "MID"},
            {"_id": ObjectId(), "position": "MID"},
        ]
        self.repo.many.return_value = players
        result = SquadService.ensure_shirt_numbers(self.repo, self.user)
        self.assertEqual([p["shirt_number"] for p in result], [1, 1, 6, 8])
        self.assertEqual(
            sum(call.args[0] == "players" for call in self.repo.update.call_args_list), 2
        )

    def test_every_generated_player_has_a_position_number_and_squad_is_unique(self):
        generator = PlayerGeneratorService(seed=123)
        for position in SHIRT_NUMBERS:
            player = generator.player("club", "BR", position)
            self.assertEqual(player["shirt_number"], SHIRT_NUMBERS[position][0])
        players = generator.squad("club", "BR")
        for player in players:
            self.assertIn(player["shirt_number"], SHIRT_NUMBERS[player["position"]])
        youth = generator.youth("club", "BR")
        self.assertEqual(len({player["shirt_number"] for player in youth}), len(youth))
        for player in youth:
            self.assertIn(player["shirt_number"], SHIRT_NUMBERS[player["position"]])

    def test_existing_automatic_numbers_are_reassigned_by_position_once(self):
        players = [
            {"_id": ObjectId(), "position": "GK", "shirt_number": 2},
            {"_id": ObjectId(), "position": "GK", "shirt_number": 3},
            {"_id": ObjectId(), "position": "ATT", "shirt_number": 4},
        ]
        self.repo.many.return_value = players
        self.assertTrue(SquadService.needs_shirt_numbers(players))
        updated = SquadService.ensure_shirt_numbers(self.repo, self.user)
        self.assertEqual([p["shirt_number"] for p in updated], [1, 12, 7])
        self.assertFalse(SquadService.needs_shirt_numbers(updated))

    def test_numbers_are_strict_integers_from_1_to_99(self):
        for value in (0, 100, -1, True, 1.5, "10"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                ShirtNumberInput(number=value)
        self.assertEqual(ShirtNumberInput(number=99).number, 99)


if __name__ == "__main__":
    unittest.main()
