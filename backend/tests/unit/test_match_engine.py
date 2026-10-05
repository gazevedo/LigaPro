import json
import unittest
from copy import deepcopy
from random import Random

from app.services.match_engine import (
    SKILLS,
    MatchConfig,
    MatchEngine,
    MatchPlayer,
    MatchTeam,
    PlayerEffectiveStrengthCalculator,
    PositionFitCalculator,
)


def team(identifier, strength=50, **kwargs):
    roles = ["GK"] + ["CB"] * 4 + ["MID"] * 4 + ["ATT"] * 2
    players = [
        MatchPlayer(
            f"{identifier}-{i}", role, role, strength=strength, skills={s: strength for s in SKILLS}
        )
        for i, role in enumerate(roles)
    ]
    return MatchTeam(identifier, players, **kwargs)


class MatchEngineTests(unittest.TestCase):
    def test_reproducibility_snapshot_and_no_mutation(self):
        home, away = team("home"), team("away")
        original = deepcopy(home)
        engine = MatchEngine()
        result = engine.simulate(home, away, 42)
        self.assertEqual(result, engine.simulate(home, away, 42))
        self.assertEqual(home, original)
        json.dumps(result)
        self.assertEqual(result["snapshot"]["home"]["lineup"][0]["energy"], 100)
        self.assertLess(result["final_lineups"][0]["lineup"][0]["energy"], 100)
        for identifier, score in result["score"].items():
            self.assertEqual(
                score,
                sum(e["type"] == "goal" and e["team_id"] == identifier for e in result["events"]),
            )
        self.assertEqual(result["events"][-1]["minute"], 90)

    def test_calibration_mode_and_telemetry_match_persisted_simulation(self):
        home, away = team("h"), team("a")
        engine = MatchEngine()
        full = engine.simulate(home, away, 543)
        compact = engine.simulate(home, away, 543, capture_snapshot=False)
        self.assertEqual(full["score"], compact["score"])
        self.assertEqual(full["events"], compact["events"])
        self.assertEqual(full["statistics"], compact["statistics"])
        self.assertNotIn("snapshot", compact)
        self.assertEqual(sum(s["possession_minutes"] for s in full["statistics"].values()), 90)
        for identity, stats in full["statistics"].items():
            self.assertEqual(stats["goals"], full["score"][identity])
            self.assertEqual(sum(stats["lanes"].values()), stats["attacks"])
            self.assertEqual(
                stats["shots"],
                sum(
                    e["team_id"] == identity
                    and e["type"] in {"goal", "shot_saved", "shot_off_target"}
                    for e in full["events"]
                ),
            )
            for phase in stats["phases"].values():
                self.assertLessEqual(phase["successes"], phase["attempts"])
        home.lineup[0].energy = 25
        self.assertEqual(away.lineup[0].energy, 100)

    def test_phase_specific_skills_and_config_validation(self):
        calculator = PlayerEffectiveStrengthCalculator(MatchConfig(), "skills")
        player = team("h").lineup[0]
        before = calculator.calculate(player, "passing")
        player.skills["goalkeeping"] += 20
        self.assertEqual(before, calculator.calculate(player, "passing"))
        self.assertEqual(calculator.calculate(player, "goalkeeping"), 70)
        for changes in (
            {"goal_base": float("nan")},
            {"phase_bases": (0.8,)},
            {"marking_attack_reduction": (0, 0.1, 2)},
        ):
            with self.assertRaises(ValueError):
                MatchConfig(**changes)

    def test_position_side_energy_morale_and_traits(self):
        config = MatchConfig()
        fit = PositionFitCalculator(config)
        player = MatchPlayer("p", "FB", "FB")
        self.assertEqual(fit.calculate(player), 1)
        player.preferred_side, player.side = "left", "right"
        side_fit = fit.calculate(player)
        player.assigned_position = "MID"
        self.assertLess(fit.calculate(player), side_fit)
        player.assigned_position = "GK"
        self.assertLess(fit.calculate(player), config.compatible_fit)
        player = MatchPlayer("p", "MID", "MID", strength=80)
        calculator = PlayerEffectiveStrengthCalculator(config, "classic")
        normal = calculator.calculate(player, "passing")
        player.morale = 100
        self.assertAlmostEqual(calculator.calculate(player, "passing") / normal, 1.04)
        player.morale, player.energy = 50, 0
        self.assertAlmostEqual(calculator.calculate(player, "passing") / normal, 0.70)
        player.energy, player.traits = 100, ("finishing",)
        self.assertEqual(calculator.calculate(player, "passing"), normal)
        self.assertGreater(calculator.calculate(player, "finishing"), normal)

    def test_focus_distribution(self):
        engine, rng = MatchEngine(), Random(5)
        for focus in ["center", "wings"]:
            lanes = [engine.attack_lane(focus, rng) for _ in range(10000)]
            ratio = sum((lane == "center") == (focus == "center") for lane in lanes) / 10000
            self.assertAlmostEqual(ratio, 0.70, delta=0.02)

    def test_skill_mode_and_legacy_documents(self):
        player = MatchPlayer.from_document({"_id": "old", "position": "GOL", "overall": 60})
        self.assertEqual((player.position, player.strength), ("GK", 60))
        engine = MatchEngine(mode="skills")
        home, away = team("h"), team("a")
        result = engine.simulate(home, away, 10)
        for player in home.lineup + away.lineup:
            player.strength = 99
        self.assertEqual(result["events"], engine.simulate(home, away, 10)["events"])
        home.lineup[0].skills.clear()
        with self.assertRaises(ValueError):
            engine.simulate(home, away, 1)

    def test_stronger_players_outweigh_home_advantage(self):
        engine = MatchEngine()
        weak, strong = team("weak", 25), team("strong", 85)
        totals = {"weak": 0, "strong": 0}
        for seed in range(250):
            result = engine.simulate(weak, strong, seed)
            for identifier, score in result["score"].items():
                totals[identifier] += score
        self.assertGreater(totals["strong"], totals["weak"] * 2)

    def test_cards_penalties_and_dismissed_participants(self):
        engine = MatchEngine(MatchConfig(foul_probability=(1, 1, 1)))
        kinds = set()
        for seed in range(40):
            result = engine.simulate(
                team("h", marking="very_heavy"), team("a", marking="very_heavy"), seed
            )
            dismissed = set()
            for event in result["events"]:
                kinds.add(event["type"])
                if event["type"] in {"chance", "goal", "foul"}:
                    self.assertNotIn(event["player_id"], dismissed)
                if event["type"] == "red_card":
                    dismissed.add(event["player_id"])
        self.assertTrue({"foul", "yellow_card", "red_card", "penalty_awarded"} <= kinds)

    def test_heavy_marking_contains_attacks_and_increases_fouls(self):
        engine = MatchEngine()
        chances, fouls = {}, {}
        for marking in ("light", "very_heavy"):
            chances[marking] = fouls[marking] = 0
            for seed in range(200):
                result = engine.simulate(team("h"), team("a", marking=marking), seed)
                chances[marking] += sum(
                    e["type"] == "chance" and e["team_id"] == "h" for e in result["events"]
                )
                fouls[marking] += sum(
                    e["type"] == "foul" and e["team_id"] == "a" for e in result["events"]
                )
        self.assertLess(chances["very_heavy"], chances["light"])
        self.assertGreater(fouls["very_heavy"], fouls["light"])

    def test_invalid_inputs_and_partial_last_block(self):
        with self.assertRaises(ValueError):
            MatchConfig(block_minutes=0)
        with self.assertRaises(ValueError):
            MatchPlayer("p", "GK", "GK", energy=float("nan"))
        with self.assertRaises(ValueError):
            MatchTeam("h", team("h").lineup, formation="4-3-3")
        home = team("h")
        home.lineup[0].id = home.lineup[1].id
        with self.assertRaises(ValueError):
            MatchEngine().simulate(home, team("a"), 1)
        result = MatchEngine(MatchConfig(block_minutes=7)).simulate(team("h"), team("a"), 1)
        self.assertEqual(result["events"][-1]["minute"], 90)
        self.assertAlmostEqual(result["final_lineups"][0]["lineup"][0]["energy"], 73)


if __name__ == "__main__":
    unittest.main()
