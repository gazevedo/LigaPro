import unittest
from copy import deepcopy

from test_match_engine import team

from app.services.match_engine import (
    MAX_SUBSTITUTIONS,
    MatchConfig,
    MatchEngine,
    MatchPlayer,
    MatchTeam,
    arrange_formation,
    bot_preset,
)


class MatchCommandTests(unittest.TestCase):
    def command(self, minute=45, **payload):
        return {"team_id": "home", "minute": minute, "type": "tactics_change", "payload": payload}

    def test_changes_only_future_blocks_and_isolates_input(self):
        home, away = team("home"), team("away")
        original = deepcopy(home)
        engine = MatchEngine()
        before = engine.simulate(home, away, 43)
        commands = [
            self.command(
                45,
                formation="3-4-3",
                play_style="all_out_attack",
                marking="heavy",
                attack_focus="wings",
            )
        ]
        changed = engine.simulate(home, away, 43, commands=commands)
        self.assertEqual(
            [e for e in before["events"] if e["minute"] <= 45],
            [
                e
                for e in changed["events"]
                if e["minute"] <= 45 and not e["type"].endswith("_change")
            ],
        )
        kinds = {e["type"] for e in changed["events"] if e["minute"] == 45}
        self.assertTrue(
            {"formation_change", "play_style_change", "marking_change", "attack_focus_change"}
            <= kinds
        )
        self.assertEqual(changed["final_lineups"][0]["formation"], "3-4-3")
        self.assertEqual(home, original)
        self.assertEqual(changed, engine.simulate(home, away, 43, commands=commands))
        self.assertEqual(changed["snapshot"]["commands"], commands)

    def test_non_boundary_command_waits_and_late_command_rejected(self):
        result = MatchEngine().simulate(
            team("home"),
            team("away"),
            7,
            commands=[self.command(46, marking="heavy"), self.command(89, marking="light")],
        )
        event = next(e for e in result["events"] if e["type"] == "marking_change")
        self.assertEqual(event["minute"], 50)
        self.assertEqual(result["events"][-1]["type"], "command_rejected")
        self.assertEqual(result["final_lineups"][0]["marking"], "heavy")

    def test_substitution_uses_actual_bench_energy_and_no_reentry(self):
        home = team("home")
        home.reserves = [MatchPlayer("bench", "ATT", "ATT", energy=90)]
        commands = [
            {
                "team_id": "home",
                "minute": 45,
                "type": "substitution",
                "payload": {"out_player_id": "home-10", "in_player_id": "bench"},
            }
        ]
        result = MatchEngine().simulate(home, team("away"), 2, commands=commands)
        event = next(e for e in result["events"] if e["type"] == "substitution")
        self.assertEqual(event["energy"], 90)
        incoming = next(p for p in result["final_lineups"][0]["lineup"] if p["id"] == "bench")
        self.assertEqual(incoming["energy"], 76.5)
        self.assertNotIn("home-10", [p["id"] for p in result["final_lineups"][0]["lineup"]])
        reverse = {
            "team_id": "home",
            "minute": 50,
            "type": "substitution",
            "payload": {"out_player_id": "bench", "in_player_id": "home-10"},
        }
        result = MatchEngine().simulate(home, team("away"), 2, commands=commands + [reverse])
        self.assertTrue(any(e["type"] == "command_rejected" for e in result["events"]))
        self.assertEqual(home.reserves[0].energy, 90)

    def test_five_substitutions_and_invalid_ids_do_not_abort(self):
        home = team("home")
        home.reserves = [MatchPlayer(f"bench-{i}", "CB", "CB") for i in range(6)]
        commands = [
            {
                "team_id": "home",
                "minute": 0,
                "type": "substitution",
                "payload": {"out_player_id": f"home-{i + 1}", "in_player_id": f"bench-{i}"},
            }
            for i in range(6)
        ]
        result = MatchEngine().simulate(home, team("away"), 3, commands=commands)
        self.assertEqual(
            sum(e["type"] == "substitution" for e in result["events"]), MAX_SUBSTITUTIONS
        )
        self.assertEqual(sum(e["type"] == "command_rejected" for e in result["events"]), 1)

    def test_formation_keeps_energy_players_and_sides(self):
        players = team("home").lineup
        players[1].energy = 31
        arranged = arrange_formation(players, "4-3-3")
        self.assertEqual({p.id for p in arranged}, {p.id for p in players})
        self.assertEqual(next(p for p in arranged if p.id == "home-1").energy, 31)
        self.assertEqual(
            {p.side for p in arranged if p.assigned_position == "FB"}, {"left", "right"}
        )
        self.assertEqual(sum(p.assigned_position == "ATT" for p in arranged), 3)

    def test_expulsion_blocks_substitution_and_cannot_restore_player(self):
        home = team("home")
        home.reserves = [MatchPlayer("bench", "CB", "CB")]
        engine = MatchEngine(MatchConfig(foul_probability=(1, 1, 1)))
        for seed in range(100):
            baseline = engine.simulate(home, team("away"), seed)
            red = next(
                (
                    e
                    for e in baseline["events"]
                    if e["type"] == "red_card" and e["team_id"] == "home" and e["minute"] < 80
                ),
                None,
            )
            if red:
                break
        self.assertIsNotNone(red)
        command = {
            "team_id": "home",
            "minute": red["minute"],
            "type": "substitution",
            "payload": {"out_player_id": red["player_id"], "in_player_id": "bench"},
        }
        result = engine.simulate(home, team("away"), seed, commands=[command])
        self.assertTrue(any(e["type"] == "command_rejected" for e in result["events"]))
        self.assertFalse(any(e["type"] == "substitution" for e in result["events"]))

    def test_snapshot_replays_bots_reserves_and_commands(self):
        home = team("home")
        home.is_bot = True
        home.reserves = [MatchPlayer("bench", "CB", "CB")]
        engine = MatchEngine()
        original = engine.simulate(
            home, team("away"), 4, commands=[self.command(45, formation="5-3-2")]
        )
        snapshot = original["snapshot"]

        def restore(data):
            return MatchTeam(
                **{
                    **data,
                    "lineup": [MatchPlayer(**p) for p in data["lineup"]],
                    "reserves": [MatchPlayer(**p) for p in data["reserves"]],
                }
            )

        replay = MatchEngine(MatchConfig(**snapshot["config"]), snapshot["mode"]).simulate(
            restore(snapshot["home"]),
            restore(snapshot["away"]),
            snapshot["seed"],
            commands=snapshot["commands"],
        )
        self.assertEqual(original, replay)

    def test_obsolete_or_invalid_commands_rejected(self):
        for payload in (
            {"pressing": "high"},
            {"tempo": "fast"},
            {"defensive_line": "high"},
            {"marking": "invalid"},
            {"formation": "2-2-6"},
        ):
            with self.assertRaises(ValueError):
                MatchEngine().simulate(
                    team("home"), team("away"), 1, commands=[self.command(**payload)]
                )

    def test_bot_presets_score_strength_profile_and_discipline(self):
        home, away = team("home"), team("away")
        self.assertEqual(bot_preset(home, away, -1), "aggressive")
        self.assertEqual(bot_preset(home, away, 1), "counter")
        self.assertEqual(bot_preset(team("weak", 30), away, 0), "defensive_heavy_marking")
        away.style = "all_out_attack"
        self.assertEqual(bot_preset(home, away, 0), "counter")
        for p in home.lineup:
            p.skills["speed"] = 80
        self.assertEqual(bot_preset(home, team("other"), 0), "counter")
        home.is_bot = True
        home.reserves = [MatchPlayer(f"bench-{i}", "CB", "CB") for i in range(6)]
        result = MatchEngine().simulate(home, away, 3)
        self.assertTrue(any(e["type"] == "play_style_change" for e in result["events"]))
        self.assertLessEqual(sum(e["type"] == "substitution" for e in result["events"]), 5)


if __name__ == "__main__":
    unittest.main()
