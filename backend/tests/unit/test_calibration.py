import unittest

from app.services.match_engine import MatchConfig, MatchEngine
from scripts.calibrate_match_engine import make_team, run_case, scenarios


class CalibrationTests(unittest.TestCase):
    def test_aggregate_uses_production_engine_and_alternates_home(self):
        case = {
            "name": "sample",
            "category": "base",
            "mode": "classic",
            "left": {"strength": 75},
            "right": {"strength": 70},
        }
        config = MatchConfig()
        result = run_case(case, 10, 123, config)
        a, b = make_team("A", strength=75), make_team("B", strength=70)
        goals = home_wins = draws = 0
        for index in range(10):
            home, away = (a, b) if index % 2 == 0 else (b, a)
            match = MatchEngine(config).simulate(home, away, 123 + index)
            goals += sum(match["score"].values())
            home_wins += match["score"][home.id] > match["score"][away.id]
            draws += match["score"][home.id] == match["score"][away.id]
        self.assertAlmostEqual(result["goals_per_match"], goals / 10)
        self.assertEqual(result["home_wins"], home_wins / 10)
        self.assertEqual(result["draws"], draws / 10)
        self.assertEqual(result["home_games_A"], 5)
        self.assertEqual(result, run_case(case, 10, 123, config))
        self.assertAlmostEqual(
            result["teams"]["A"]["possession"] + result["teams"]["B"]["possession"], 1
        )

    def test_controlled_axes_and_tactic_coverage(self):
        cases = scenarios()
        self.assertEqual(len({case["name"] for case in cases}), len(cases))
        self.assertEqual(sum(case["category"] == "tactics" for case in cases), 36)
        self.assertEqual(sum(case["category"] == "quality" for case in cases), 9)
        self.assertEqual(sum(case["category"] == "base" for case in cases), 6)
        skill_cases = [
            case
            for case in cases
            if case["category"] == "attributes" and case["name"] != "skills_50"
        ]
        self.assertEqual(len(skill_cases), 6)
        self.assertTrue(all(len(case["left"]["skills"]) == 1 for case in skill_cases))
        for case in cases:
            make_team("A", **case["left"])
            make_team("B", **case["right"])

    def test_fits_and_sides_preserve_assigned_formation(self):
        correct = make_team("A", fit="correct", side="correct")
        opposite = make_team("A", fit="correct", side="opposite")
        wrong = make_team("A", fit="wrong", side="correct")
        self.assertEqual(
            [p.assigned_position for p in correct.lineup],
            [p.assigned_position for p in wrong.lineup],
        )
        self.assertEqual(correct.lineup[0].position, "GK")
        for normal, reversed_side in zip(correct.lineup, opposite.lineup):
            if normal.side != "center":
                self.assertEqual(normal.preferred_side, normal.side)
                self.assertNotEqual(reversed_side.preferred_side, reversed_side.side)


if __name__ == "__main__":
    unittest.main()
