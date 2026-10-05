import unittest
from random import Random

from test_match_engine import team

from app.services.discipline import DuelResolver, FoulResolver, PenaltyService
from app.services.match_engine import MatchConfig, MatchEngine


class Draws:
    def __init__(self, *values):
        self.values = iter(values)

    def random(self):
        return next(self.values)


class DisciplineTests(unittest.TestCase):
    def test_duel_uses_actual_players_and_strength(self):
        attacker, defender = team("h").lineup[10], team("a").lineup[1]
        won = DuelResolver.resolve(attacker, defender, 90, 10, Draws(0.5))
        lost = DuelResolver.resolve(attacker, defender, 10, 90, Draws(0.5))
        self.assertEqual(won["winner_id"], attacker.id)
        self.assertEqual(lost["winner_id"], defender.id)
        self.assertEqual(won["attacker_id"], attacker.id)
        self.assertEqual(won["defender_id"], defender.id)

    def test_foul_severity_card_and_penalty_area(self):
        attacker = team("h").lineup[10]
        duel = {"winner_id": attacker.id}
        resolver = FoulResolver(MatchConfig())
        self.assertIsNone(resolver.resolve(duel, attacker, 2, Draws(0.9)))
        direct = resolver.resolve(duel, attacker, 2, Draws(0, 0.01, 0))
        self.assertEqual(direct["card"], "direct_red")
        self.assertTrue(direct["penalty_area"])
        yellow = resolver.resolve(duel, attacker, 2, Draws(0, 0.2, 0.9))
        self.assertEqual(yellow["card"], "yellow")
        self.assertFalse(yellow["penalty_area"])
        ordinary = resolver.resolve(duel, attacker, 2, Draws(0, 0.8, 0.9))
        self.assertIsNone(ordinary["card"])

    def test_second_yellow_and_direct_red_removal_and_sectors(self):
        for direct in (False, True):
            engine = MatchEngine(
                MatchConfig(
                    foul_probability=(1, 1, 1),
                    yellow_probability=(1, 1, 1),
                    direct_red_probability=(1, 1, 1) if direct else (0, 0, 0),
                    penalty_area_probability=(0, 0, 0),
                )
            )
            result = engine.simulate(team("h"), team("a"), 7)
            red = [e for e in result["events"] if e["type"] == "red_card"]
            self.assertTrue(red)
            self.assertEqual(
                {e["reason"] for e in red}, {"direct_red" if direct else "second_yellow"}
            )
            for index, identity in enumerate(("h", "a")):
                removed = {e["player_id"] for e in red if e["team_id"] == identity}
                final = result["final_lineups"][index]
                self.assertEqual(len(final["lineup"]), 11 - len(removed))
                self.assertFalse(removed & {p["id"] for p in final["lineup"]})
                self.assertEqual(set(final["dismissed_player_ids"]), removed)
                for event in red:
                    if event["team_id"] == identity:
                        for later in result["events"]:
                            if later["minute"] > event["minute"] and later["type"] == "duel":
                                self.assertNotIn(
                                    event["player_id"], (later["attacker_id"], later["defender_id"])
                                )

    def test_penalty_service_reproducibility(self):
        engine = MatchEngine()
        service = PenaltyService(engine.calculator, engine.goalkeeper, engine.finishing)
        shooter, keeper = team("h").lineup[10], team("a").lineup[0]
        self.assertEqual(
            service.resolve(shooter, keeper, Random(42)),
            service.resolve(shooter, keeper, Random(42)),
        )

    def test_config_rejects_bad_discipline_values(self):
        for values in (
            {"foul_marking_modifiers": (1, -1, 1)},
            {"yellow_probability": (0, 0, 0)},
            {"penalty_area_probability": (0, 0, 2)},
        ):
            with self.assertRaises(ValueError):
                MatchConfig(**values)
