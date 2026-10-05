"""Seeded, paired Monte Carlo calibration; uses the production engine without MongoDB.

Run from the repository: PYTHONPATH=backend python backend/scripts/calibrate_match_engine.py
"""

import argparse
import hashlib
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from itertools import combinations, product
from pathlib import Path
from time import perf_counter

from app.services.match_engine import SKILLS, MatchConfig, MatchEngine, MatchPlayer, MatchTeam


def make_team(identity, **options):
    strength = options.get("strength", 70)
    formation = options.get("formation", "4-4-2")
    defense, midfield, attack = map(int, formation.split("-"))
    roles = ["GK"] + ["FB"] * 2 + ["CB"] * (defense - 2) + ["MID"] * midfield + ["ATT"] * attack
    players = []
    for index, role in enumerate(roles):
        side = "center"
        if role == "FB" or (role == "MID" and index in (defense + 1, defense + 2)):
            side = "left" if index % 2 else "right"
        natural = role
        if role != "GK":
            natural = {
                "compatible": {"FB": "CB", "CB": "FB", "MID": "ATT", "ATT": "MID"},
                "wrong": {"FB": "ATT", "CB": "ATT", "MID": "CB", "ATT": "CB"},
            }
            natural = natural.get(options.get("fit"), {}).get(role, role)
        preferred = options.get("side", "both")
        if preferred == "correct":
            preferred = side if side != "center" else "both"
        elif preferred == "opposite":
            preferred = {"left": "right", "right": "left", "center": "both"}[side]
        skills = {skill: options.get("skill_strength", strength) for skill in sorted(SKILLS)}
        skills.update(options.get("skills", {}))
        players.append(
            MatchPlayer(
                f"{identity}-{index}",
                natural,
                role,
                strength=strength,
                energy=options.get("energy", 100),
                morale=options.get("morale", 50),
                side=side,
                preferred_side=preferred,
                skills=skills,
            )
        )
    return MatchTeam(
        identity,
        players,
        formation,
        options.get("style", "balanced"),
        options.get("marking", "light"),
        options.get("focus", "normal"),
    )


def scenarios():
    cases = []

    def add(name, category, left=None, right=None, mode="classic"):
        cases.append(
            {
                "name": name,
                "category": category,
                "left": left or {},
                "right": right or {},
                "mode": mode,
            }
        )

    for a, b in ((70, 70), (75, 70), (80, 60), (60, 80), (90, 40), (40, 90)):
        add(f"base_{a}_{b}", "base", {"strength": a}, {"strength": b})
    add("skills_50", "attributes", {"skill_strength": 50}, {"skill_strength": 50}, "skills")
    for skill in ("passing", "playmaking", "finishing", "tackling", "goalkeeping", "speed"):
        add(
            f"skill_{skill}_70",
            "attributes",
            {"skill_strength": 50, "skills": {skill: 70}},
            {"skill_strength": 50},
            "skills",
        )
    for fit in ("correct", "compatible", "wrong"):
        add(f"fit_{fit}", "position", {"fit": fit})
    for side in ("correct", "opposite", "both"):
        add(f"side_{side}", "side", {"side": side})
    for energy in (100, 80, 60, 40):
        add(f"energy_{energy}", "energy", {"energy": energy})
    for morale in (0, 50, 100):
        add(f"morale_{morale}", "morale", {"morale": morale})
    for formation in ("4-4-2", "4-3-3", "5-3-2", "3-5-2"):
        add(f"formation_{formation}", "formation", {"formation": formation})
    for left, right in (
        ("balanced", "balanced"),
        ("all_out_attack", "balanced"),
        ("counter_attack", "balanced"),
        ("counter_attack", "all_out_attack"),
    ):
        add(f"style_{left}_{right}", "style", {"style": left}, {"style": right})
    for marking in ("light", "heavy", "very_heavy"):
        add(f"marking_{marking}", "marking", {"marking": marking})
    for focus in ("normal", "center", "wings"):
        add(f"focus_{focus}", "focus", {"focus": focus})
    tactics = list(
        product(("balanced", "all_out_attack", "counter_attack"), ("light", "heavy", "very_heavy"))
    )
    for a, b in combinations(tactics, 2):
        add(
            f"tactic_{a[0]}_{a[1]}__{b[0]}_{b[1]}",
            "tactics",
            {"style": a[0], "marking": a[1]},
            {"style": b[0], "marking": b[1]},
        )
    # Verify that tactics cannot overturn a large gap in squad quality.
    for a in tactics:
        add(
            f"quality_40_{a[0]}_{a[1]}_90",
            "quality",
            {"strength": 40, "style": a[0], "marking": a[1]},
            {"strength": 90},
        )
    return cases


def run_case(case, matches, seed, config):
    engine = MatchEngine(config, mode=case["mode"])
    left, right = make_team("A", **case["left"]), make_team("B", **case["right"])
    totals = {identity: {} for identity in ("A", "B")}
    wins, home_wins, draws, away_wins = 0, 0, 0, 0
    for index in range(matches):
        home, away = (left, right) if index % 2 == 0 else (right, left)
        result = engine.simulate(home, away, seed + index, capture_snapshot=False)
        a, b = result["score"]["A"], result["score"]["B"]
        wins += a > b
        draws += a == b
        home_wins += result["score"][home.id] > result["score"][away.id]
        away_wins += result["score"][home.id] < result["score"][away.id]
        for identity, stats in result["statistics"].items():
            flattened = {
                key: value for key, value in stats.items() if key not in {"phases", "lanes"}
            }
            flattened.update({f"lane_{lane}": count for lane, count in stats["lanes"].items()})
            for phase, phase_stats in stats["phases"].items():
                flattened.update({f"{phase}_{key}": value for key, value in phase_stats.items()})
            for key, value in flattened.items():
                totals[identity][key] = totals[identity].get(key, 0) + value
    averages = {
        identity: {key: value / matches for key, value in stats.items()}
        for identity, stats in totals.items()
    }
    for stats in averages.values():
        for phase in ("build", "progress", "create"):
            stats[f"{phase}_success_rate"] = stats[f"{phase}_successes"] / max(
                1e-9, stats[f"{phase}_attempts"]
            )
        stats["chance_efficiency"] = stats["chances"] / max(1e-9, stats["attacks"])
        stats["shot_conversion"] = stats["goals"] / max(1e-9, stats["shots"])
        stats["transition_efficiency"] = stats["transition_chances"] / max(
            1e-9, stats["transitions"]
        )
    return {
        **case,
        "matches": matches,
        "seed": seed,
        "home_games_A": (matches + 1) // 2,
        "wins_A": wins / matches,
        "draws": draws / matches,
        "wins_B": (matches - wins - draws) / matches,
        "home_wins": home_wins / matches,
        "away_wins": away_wins / matches,
        "goals_per_match": averages["A"]["goals"] + averages["B"]["goals"],
        "teams": averages,
    }


def discipline_acceptance(results, matches):
    cases = {r["name"]: r for r in results}
    names = ["marking_" + marking for marking in ("light", "heavy", "very_heavy")]
    if not all(name in cases for name in names):
        return []
    checks = [{"name": "discipline_sample_size", "passed": matches >= 10000, "detail": matches}]
    for field in ("fouls", "yellow_cards", "red_cards"):
        values = [cases[name]["teams"]["A"][field] for name in names]
        checks.append(
            {
                "name": field + "_increases",
                "passed": values[0] < values[1] < values[2],
                "detail": values,
            }
        )
    for side, field in (("B", "attacks"), ("A", "build_success_rate")):
        values = [cases[name]["teams"][side][field] for name in names]
        checks.append(
            {
                "name": side + "_" + field + "_decreases",
                "passed": values[0] > values[1] > values[2],
                "detail": values,
            }
        )
    return checks


def acceptance(results, matches):
    by_name = {result["name"]: result for result in results}
    checks = []

    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    def team(name, identity="A"):
        return by_name[name]["teams"][identity]

    baseline = by_name["base_70_70"]
    check("sample_size", matches >= 10000 and all(r["matches"] >= 10000 for r in results), matches)
    check("equal_goals", 2.2 <= baseline["goals_per_match"] <= 2.9, baseline["goals_per_match"])
    check("equal_draws", 0.22 <= baseline["draws"] <= 0.32, baseline["draws"])
    edge = baseline["home_wins"] - baseline["away_wins"]
    check("small_home_advantage", 0 < edge < 0.06, edge)
    for name in ("base_75_70", "base_80_60", "base_90_40"):
        r = by_name[name]
        check(name + "_quality", r["wins_A"] > r["wins_B"], r["wins_A"] - r["wins_B"])
    for name in ("base_60_80", "base_40_90"):
        r = by_name[name]
        check(name + "_quality", r["wins_B"] > r["wins_A"], r["wins_B"] - r["wins_A"])
    control = team("skills_50")
    attributes = {
        "passing": "build_success_rate",
        "playmaking": "create_success_rate",
        "finishing": "shot_conversion",
        "tackling": "chances",
        "goalkeeping": "shot_conversion",
        "speed": "progress_success_rate",
    }
    for skill, metric in attributes.items():
        identity = "B" if skill in {"tackling", "goalkeeping"} else "A"
        changed = team(f"skill_{skill}_70", identity)[metric]
        reference = team("skills_50", identity)[metric]
        improved = changed < reference if identity == "B" else changed > reference
        check(
            f"attribute_{skill}",
            improved,
            {"metric": metric, "baseline": reference, "changed": changed},
        )
        rate = by_name[f"skill_{skill}_70"]["wins_A"]
        check(f"attribute_{skill}_bounded", rate < 0.65, rate)
    # Keeper/finishing never enter initiative; their paired possession is equal up to
    # stochastic downstream effects (cards and phase completion alter RNG consumption).
    for skill in ("goalkeeping", "finishing"):
        delta = abs(team(f"skill_{skill}_70")["possession"] - control["possession"])
        check(f"attribute_{skill}_phase_local", delta < 0.015, delta)
    fits = [team(f"fit_{fit}")["goals"] for fit in ("correct", "compatible", "wrong")]
    check("position_penalties", fits[0] > fits[1] > fits[2] > fits[0] * 0.45, fits)
    opposite, both = team("side_opposite")["goals"], team("side_both")["goals"]
    check("side_penalty_smaller", 0 < both - opposite < fits[0] - fits[1], both - opposite)
    check("both_equals_correct", abs(team("side_correct")["goals"] - both) < 0.04, both)
    energies = [team(f"energy_{energy}")["goals"] for energy in (100, 80, 60, 40)]
    check("gradual_energy", all(a > b for a, b in zip(energies, energies[1:])), energies)
    moral = [by_name[f"morale_{value}"]["wins_A"] for value in (0, 50, 100)]
    check(
        "small_morale_effect", moral[0] < moral[1] < moral[2] and moral[2] - moral[0] < 0.12, moral
    )
    for r in results:
        if r["category"] == "formation":
            check(r["name"] + "_bounded", 0.25 < r["wins_A"] < 0.50, r["wins_A"])
    balanced = team("style_balanced_balanced")
    offensive = by_name["style_all_out_attack_balanced"]
    check(
        "all_out_more_chances_both",
        offensive["teams"]["A"]["chances"] > balanced["chances"]
        and offensive["teams"]["B"]["chances"] > balanced["chances"],
        [offensive["teams"]["A"]["chances"], offensive["teams"]["B"]["chances"]],
    )
    counter = team("style_counter_attack_balanced")
    transition = team("style_counter_attack_all_out_attack")
    check(
        "counter_lower_volume",
        counter["possession"] < balanced["possession"] and counter["attacks"] < balanced["attacks"],
        counter["possession"],
    )
    check(
        "counter_transition_efficiency",
        transition["transition_efficiency"] > counter["chance_efficiency"],
        [counter["chance_efficiency"], transition["transition_efficiency"]],
    )
    light, heavy = team("marking_light"), team("marking_very_heavy")
    reduction = (
        1 - team("marking_very_heavy", "B")["attacks"] / team("marking_light", "B")["attacks"]
    )
    check("marking_attack_reduction", 0.12 < reduction < 0.24, reduction)
    check(
        "marking_cost",
        heavy["build_success_rate"] < light["build_success_rate"],
        [light["build_success_rate"], heavy["build_success_rate"]],
    )
    check(
        "marking_more_fouls_cards",
        heavy["fouls"] > light["fouls"]
        and heavy["yellow_cards"] > light["yellow_cards"]
        and heavy["red_cards"] > light["red_cards"],
        heavy["fouls"],
    )
    for focus in ("center", "wings"):
        stats = team(f"focus_{focus}")
        chosen = (
            stats["lane_center"] if focus == "center" else stats["lane_left"] + stats["lane_right"]
        )
        ratio = chosen / stats["attacks"]
        check(f"focus_{focus}_70_percent", 0.68 < ratio < 0.72, ratio)
    beaten = {}
    for r in results:
        if r["category"] != "tactics":
            continue
        a = (r["left"]["style"], r["left"]["marking"])
        b = (r["right"]["style"], r["right"]["marking"])
        beaten.setdefault(a, 0)
        beaten.setdefault(b, 0)
        if r["wins_A"] > r["wins_B"] + 0.02:
            beaten[a] += 1
        if r["wins_B"] > r["wins_A"] + 0.02:
            beaten[b] += 1
    check(
        "no_dominant_tactic",
        max(beaten.values(), default=0) < 8,
        {"/".join(key): value for key, value in beaten.items()},
    )
    for r in results:
        if r["category"] == "quality":
            check(
                r["name"] + "_squad_dominates",
                r["wins_B"] > r["wins_A"] + 0.25,
                r["wins_B"] - r["wins_A"],
            )
    return checks


def markdown(report):
    sample_size = f"{report['matches_per_scenario']:,}".replace(",", ".")
    lines = [
        "# Calibração do motor — Script 6",
        "",
        f"{len(report['results'])} cenários × {sample_size} partidas; "
        f"seed inicial {report['seed']}, mando alternado. "
        "Posse corresponde aos minutos de iniciativa dos blocos, não a tracking de bola.",
        "",
        "Resultados completos, configuração, hash do motor e métricas por fase no JSON adjacente. "
        "A identifica a equipe sob teste; B é seu adversário. Nas variações de energia, moral, "
        "lado e habilidades, somente A recebe a mudança; gols/jogo somam as duas equipes.",
        "",
        "| Cenário | Gols/jogo | Gols A/B | Empates | Vitórias A | "
        "Posse A | Ataques A/B | Chances A/B |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in report["results"]:
        a, b = result["teams"]["A"], result["teams"]["B"]
        lines.append(
            f"| {result['name']} | {result['goals_per_match']:.3f} | "
            f"{a['goals']:.3f}/{b['goals']:.3f} | {result['draws']:.1%} | "
            f"{result['wins_A']:.1%} | {a['possession']:.1%} | "
            f"{a['attacks']:.2f}/{b['attacks']:.2f} | "
            f"{a['chances']:.2f}/{b['chances']:.2f} |"
        )
    lines += [
        "",
        "## Finalizações, faltas, cartões e setores",
        "",
        "Valores médios por partida para a equipe A; dados das duas equipes no JSON.",
        "",
        "| Cenário | Finalizações | Faltas | Amarelos | Vermelhos | "
        "Centro | Alas | Chances/ataque |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in report["results"]:
        if result["category"] in {"tactics", "quality"}:
            continue
        a = result["teams"]["A"]
        center = a["lane_center"] / max(1e-9, a["attacks"])
        lines.append(
            f"| {result['name']} | {a['shots']:.2f} | {a['fouls']:.3f} | "
            f"{a['yellow_cards']:.3f} | {a['red_cards']:.3f} | {center:.1%} | "
            f"{1 - center:.1%} | {a['chance_efficiency']:.1%} |"
        )
    lines += [
        "",
        "## Habilidades e fases",
        "",
        "A/B são as equipes definidas em cada cenário, com mando alternado. "
        "Construção, progressão e criação são taxas condicionais de sucesso da fase; "
        "conversão inclui pênaltis.",
        "",
        "| Cenário | Construção A/B | Progressão A/B | Criação A/B | Conversão A/B |",
        "|---|---:|---:|---:|---:|",
    ]
    for result in report["results"]:
        if result["category"] != "attributes":
            continue
        a, b = result["teams"]["A"], result["teams"]["B"]
        fields = (
            "build_success_rate",
            "progress_success_rate",
            "create_success_rate",
            "shot_conversion",
        )
        values = [f"{a[key]:.1%}/{b[key]:.1%}" for key in fields]
        lines.append(f"| {result['name']} | " + " | ".join(values) + " |")
    lines += ["", "## Critérios de aceitação", ""]
    for check in report["acceptance"]:
        lines.append(
            f"- {'PASS' if check['passed'] else 'FAIL'} — {check['name']}: "
            f"`{json.dumps(check['detail'], ensure_ascii=False)}`"
        )
    lines += [
        "",
        "## Limites da medição",
        "",
        "As matrizes cobrem três estilos × três marcações, "
        "com forças, formação e foco controlados. "
        "Dominância significa superar cada alternativa por mais de 2 pontos percentuais "
        "na diferença "
        "entre vitórias e derrotas; não é uma prova sobre todas as escalações possíveis. "
        "A amostragem usa os mesmos seeds por cenário; variações pequenas "
        "ainda têm incerteza estatística. "
        "Moral limita a força efetiva a ±4%; a variação de vitórias não é esse multiplicador.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matches", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--categories", nargs="+", choices=sorted({case["category"] for case in scenarios()})
    )
    parser.add_argument("--output", type=Path, default=Path("docs/calibration-script-06.json"))
    args = parser.parse_args()
    if args.matches < 2 or args.matches % 2 or args.workers < 1:
        parser.error("Use a positive even match count and at least one worker")
    cases = [
        case for case in scenarios() if not args.categories or case["category"] in args.categories
    ]
    config, results = MatchConfig(), []
    start = perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(run_case, case, args.matches, args.seed, config): case for case in cases
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(
                f"{len(results)}/{len(cases)} {result['name']}: "
                f"gols={result['goals_per_match']:.3f} empates={result['draws']:.1%}",
                flush=True,
            )
    order = {case["name"]: index for index, case in enumerate(cases)}
    results.sort(key=lambda r: order[r["name"]])
    engine_path = Path(__file__).resolve().parents[1] / "app/services/match_engine.py"
    complete = len(cases) == len(scenarios())
    report = {
        "matches_per_scenario": args.matches,
        "total_matches": len(cases) * args.matches,
        "seed": args.seed,
        "config": asdict(config),
        "engine_sha256": hashlib.sha256(engine_path.read_bytes()).hexdigest(),
        "discipline_sha256": hashlib.sha256(
            engine_path.with_name("discipline.py").read_bytes()
        ).hexdigest(),
        "results": results,
        "acceptance": (acceptance(results, args.matches) if complete else [])
        + discipline_acceptance(results, args.matches),
        "elapsed_seconds": perf_counter() - start,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    args.output.with_suffix(".md").write_text(markdown(report))
    failures = [check["name"] for check in report["acceptance"] if not check["passed"]]
    print(f"Report: {args.output}; failures: {failures}", flush=True)
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
