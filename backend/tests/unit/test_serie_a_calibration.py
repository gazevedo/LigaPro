import unittest
from unittest.mock import patch

from scripts.calibrate_serie_a import calibrate, pattern_summary, render_report, run_season


class ScheduledEngine:
    """Controlled outcomes exercise streak boundaries and season accounting."""

    def __init__(self):
        self.calls = []

    def simulate(self, home, away, seed, capture_snapshot=False):
        self.calls.append((home.id, away.id, home.style, home.marking, seed))
        # Focal club wins round three, resetting two draws, then always draws.
        score = {home.id: 0, away.id: 0}
        if 20 <= len(self.calls) - 1 < 30 and "club-01" in score:
            score["club-01"] = 1
        return {"score": score}


class SerieACalibrationTests(unittest.TestCase):
    def test_full_schedule_table_and_strategy_accounting(self):
        engine = ScheduledEngine()
        season = run_season(35, engine=engine)
        self.assertEqual(len(engine.calls), 380)
        fixtures = [(home, away) for home, away, *_ in engine.calls]
        self.assertEqual(len(set(fixtures)), 380)
        for home, away in fixtures:
            self.assertIn((away, home), fixtures)
        self.assertEqual(
            sum(row["wins"] for row in season["table"]),
            sum(row["losses"] for row in season["table"]),
        )
        for row in season["table"]:
            self.assertEqual(row["wins"] + row["draws"] + row["losses"], 38)
            self.assertEqual(row["points"], 3 * row["wins"] + row["draws"])
            self.assertEqual(len(row["strategies_used"]), 1)
            self.assertEqual(sum(s["games"] for s in row["strategies_used"].values()), 38)
        self.assertEqual(season["changes"], [])

    def test_change_after_three_non_wins_resets_on_win_and_changes_next_round(self):
        engine = ScheduledEngine()
        season = run_season(35, adaptive_club="club-01", engine=engine)
        self.assertEqual(season["changes"][0]["after_round"], 6)
        self.assertTrue(all(change["non_winning_streak"] == 3 for change in season["changes"]))
        self.assertTrue(all(change["after_round"] < 38 for change in season["changes"]))
        focal_home = [call for call in engine.calls if call[0] == "club-01"]
        self.assertEqual(focal_home[0][2:4], ("balanced", "light"))
        for call in focal_home:
            round_index = (call[4] - 35) // 10
            if round_index < 6:
                self.assertEqual(call[2:4], ("balanced", "light"))
            elif round_index < 9:
                self.assertEqual(call[2:4], ("balanced", "heavy"))
        for row in season["table"]:
            if row["club_id"] != "club-01":
                self.assertEqual(len(row["strategies_used"]), 1)
            for key in ("wins", "draws", "losses"):
                self.assertEqual(sum(s[key] for s in row["strategies_used"].values()), row[key])

    def test_aggregate_balances_strategy_assignments_and_compares_paired_club(self):
        class DrawEngine:
            def simulate(self, home, away, seed, capture_snapshot=False):
                return {"score": {home.id: 0, away.id: 0}}

        def pair(task):
            seed, rotation, focal, streak = task
            return dict(
                fixed=run_season(seed, rotation, engine=DrawEngine()),
                adaptive=run_season(seed, rotation, focal, streak, DrawEngine()),
            )

        with patch("scripts.calibrate_serie_a.run_pair", side_effect=pair):
            report = calibrate(list(range(10)), workers=1)
        self.assertEqual(report["total_matches"], 68400)
        self.assertEqual(len(report["comparisons"]), 90)
        self.assertFalse(report["dominant_strategy_detected"])
        self.assertEqual(report["adaptive_points_delta"]["mean"], 0)
        self.assertTrue(
            all(
                value["mean"] == 1 and value["samples"] == 10
                for value in report["strategy_points_per_game"].values()
            )
        )
        rendered = render_report(report)
        self.assertIn("Clube Série A 20", rendered)
        self.assertIn("## Troca após 3 jogos sem vitória", rendered)
        self.assertIn("Nenhuma estratégia atingiu", rendered)
        first_seed = report["seasons"][:9]
        for club_index in range(20):
            club = f"club-{club_index + 1:02d}"
            starting = {
                row["initial_strategy"]
                for pair in first_seed
                for row in pair["fixed"]["table"]
                if row["club_id"] == club
            }
            self.assertEqual(len(starting), 9)

    def test_marking_pattern_distinguishes_consistent_effect_from_single_style_leader(self):
        samples = {
            f"{style}/{marking}": [value] * 10
            for style in ("balanced", "all_out_attack", "counter_attack")
            for marking, value in (("light", 1.0), ("heavy", 1.1), ("very_heavy", 1.3))
        }
        result = pattern_summary(samples)
        self.assertTrue(result["very_heavy_best_in_each_style"])
        self.assertAlmostEqual(result["marking_vs_light"]["very_heavy"]["mean"], 0.3)
        samples["balanced/heavy"] = [1.5] * 10
        self.assertFalse(pattern_summary(samples)["very_heavy_best_in_each_style"])

    def test_production_engine_is_reproducible_and_fixed_and_adaptive_start_paired(self):
        fixed = run_season(123)
        self.assertEqual(fixed, run_season(123))
        adaptive = run_season(123, adaptive_club="club-01", bad_streak=39)
        self.assertEqual(fixed["table"], adaptive["table"])
        self.assertEqual(adaptive["changes"], [])
        with self.assertRaises(ValueError):
            run_season(123, bad_streak=0)


if __name__ == "__main__":
    unittest.main()
