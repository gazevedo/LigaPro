"""Controlled Serie A calibration using the production engine, without MongoDB."""

import argparse
import hashlib
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from itertools import product
from pathlib import Path
from statistics import mean, stdev

from app.services.competition import ranked, round_robin
from app.services.match_engine import MatchConfig, MatchEngine
from scripts.calibrate_match_engine import make_team

STRATEGIES = list(
    product(
        ("balanced", "all_out_attack", "counter_attack"),
        ("light", "heavy", "very_heavy"),
    )
)


def strategy_name(index):
    return "/".join(STRATEGIES[index])


def run_season(seed, rotation=0, adaptive_club=None, bad_streak=3, engine=None):
    if bad_streak < 1:
        raise ValueError("bad_streak must be positive")
    engine = engine or MatchEngine()
    ids = [f"club-{i + 1:02d}" for i in range(20)]
    if adaptive_club is not None and adaptive_club not in ids:
        raise ValueError("Unknown adaptive club")
    tactics = {identity: (i + rotation) % len(STRATEGIES) for i, identity in enumerate(ids)}
    initial = tactics.copy()
    streaks = Counter()
    usage = {identity: {} for identity in ids}
    changes = []
    rows = {
        identity: dict(
            _id=identity,
            club_id=identity,
            name=f"Clube Série A {i + 1:02d}",
            points=0,
            wins=0,
            draws=0,
            losses=0,
            goals_for=0,
            goals_against=0,
            goal_difference=0,
        )
        for i, identity in enumerate(ids)
    }
    for round_index, fixtures in enumerate(round_robin(ids)):
        for match_index, (home, away) in enumerate(fixtures):
            teams = [
                make_team(
                    identity,
                    style=STRATEGIES[tactics[identity]][0],
                    marking=STRATEGIES[tactics[identity]][1],
                )
                for identity in (home, away)
            ]
            result = engine.simulate(
                *teams, seed + round_index * 10 + match_index, capture_snapshot=False
            )
            for identity, opponent in ((home, away), (away, home)):
                goals, conceded = result["score"][identity], result["score"][opponent]
                outcome = "wins" if goals > conceded else "draws" if goals == conceded else "losses"
                row = rows[identity]
                row[outcome] += 1
                row["points"] += 3 if outcome == "wins" else 1 if outcome == "draws" else 0
                row["goals_for"] += goals
                row["goals_against"] += conceded
                row["goal_difference"] = row["goals_for"] - row["goals_against"]
                name = strategy_name(tactics[identity])
                record = usage[identity].setdefault(name, dict(games=0, wins=0, draws=0, losses=0))
                record["games"] += 1
                record[outcome] += 1
                streaks[identity] = 0 if outcome == "wins" else streaks[identity] + 1
        # Changes take effect next round, never retroactively or after the final round.
        if adaptive_club and streaks[adaptive_club] >= bad_streak and round_index < 37:
            old = tactics[adaptive_club]
            tactics[adaptive_club] = (old + 1) % len(STRATEGIES)
            changes.append(
                dict(
                    club_id=adaptive_club,
                    after_round=round_index + 1,
                    non_winning_streak=streaks[adaptive_club],
                    previous=strategy_name(old),
                    next=strategy_name(tactics[adaptive_club]),
                )
            )
            streaks[adaptive_club] = 0
    table = ranked(list(rows.values()))
    for position, row in enumerate(table, 1):
        identity = row["club_id"]
        row.update(
            position=position,
            games=38,
            initial_strategy=strategy_name(initial[identity]),
            final_strategy=strategy_name(tactics[identity]),
            strategies_used=usage[identity],
        )
    return dict(
        seed=seed,
        rotation=rotation,
        adaptive_club=adaptive_club,
        matches=380,
        table=table,
        changes=changes,
    )


def interval(values):
    average = mean(values)
    margin = 1.96 * stdev(values) / len(values) ** 0.5 if len(values) > 1 else None
    return dict(
        samples=len(values),
        mean=average,
        approximate_95_interval=None if margin is None else [average - margin, average + margin],
    )


def pattern_summary(samples):
    styles = ("balanced", "all_out_attack", "counter_attack")
    markings = ("light", "heavy", "very_heavy")
    count = len(next(iter(samples.values())))
    marking_samples = {
        marking: [mean(samples[f"{style}/{marking}"][i] for style in styles) for i in range(count)]
        for marking in markings
    }
    return dict(
        marking_points_per_game={
            name: interval(values) for name, values in marking_samples.items()
        },
        marking_vs_light={
            name: interval([a - b for a, b in zip(values, marking_samples["light"])])
            for name, values in marking_samples.items()
            if name != "light"
        },
        very_heavy_best_in_each_style=all(
            mean(samples[f"{style}/very_heavy"]) > mean(samples[f"{style}/{marking}"])
            for style in styles
            for marking in ("light", "heavy")
        ),
    )


def run_pair(task):
    seed, rotation, focal, bad_streak = task
    # Disjoint match-seed ranges between independent seed blocks.
    return dict(
        fixed=run_season(seed * 1000, rotation),
        adaptive=run_season(seed * 1000, rotation, focal, bad_streak),
    )


def calibrate(seeds, bad_streak=3, workers=4):
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("Provide distinct seeds")
    if workers < 1 or bad_streak < 1:
        raise ValueError("workers and bad_streak must be positive")
    tasks = [
        (seed, rotation, f"club-{i % 20 + 1:02d}", bad_streak)
        for i, seed in enumerate(seeds)
        for rotation in range(9)
    ]
    if workers == 1:
        pairs = list(map(run_pair, tasks))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            pairs = list(pool.map(run_pair, tasks))
    seasons, comparisons = [], []
    strategy_samples = {strategy_name(i): [] for i in range(9)}
    # Every club receives each starting strategy once per seed, balancing schedule and identity.
    for seed_index, seed in enumerate(seeds):
        focal = f"club-{seed_index % 20 + 1:02d}"
        for rotation in range(9):
            pair = pairs[seed_index * 9 + rotation]
            fixed, adaptive = pair["fixed"], pair["adaptive"]
            seasons.append(dict(fixed=fixed, adaptive=adaptive))
            a = next(row for row in fixed["table"] if row["club_id"] == focal)
            b = next(row for row in adaptive["table"] if row["club_id"] == focal)
            comparisons.append(
                dict(
                    seed=seed,
                    rotation=rotation,
                    club_id=focal,
                    initial_strategy=a["initial_strategy"],
                    fixed_points=a["points"],
                    adaptive_points=b["points"],
                    points_delta=b["points"] - a["points"],
                    fixed_position=a["position"],
                    adaptive_position=b["position"],
                    changes=len(adaptive["changes"]),
                )
            )
        for name in strategy_samples:
            rows = [
                row
                for pair in seasons[-9:]
                for row in pair["fixed"]["table"]
                if row["initial_strategy"] == name
            ]
            strategy_samples[name].append(
                sum(row["points"] for row in rows) / sum(row["games"] for row in rows)
            )
    summary = {name: interval(values) for name, values in strategy_samples.items()}
    leader = max(summary, key=lambda name: summary[name]["mean"])
    differences = {
        name: interval([a - b for a, b in zip(strategy_samples[leader], values)])
        for name, values in strategy_samples.items()
        if name != leader
    }
    dominant = len(seeds) >= 10 and all(
        value["approximate_95_interval"][0] > 0.06 for value in differences.values()
    )
    adaptive_by_seed = [
        mean(row["points_delta"] for row in comparisons if row["seed"] == seed) for seed in seeds
    ]
    return dict(
        methodology=dict(
            clubs=20,
            rounds=38,
            strength=70,
            formation="4-4-2",
            seeds=seeds,
            rotations=9,
            bad_streak=bad_streak,
            switching=(
                "Cycle through nine strategies after consecutive non-wins; "
                "reset streak after switching"
            ),
            mode="classic",
            engine_config=asdict(MatchConfig()),
            engine_sha256=hashlib.sha256(
                (Path(__file__).resolve().parents[1] / "app/services/match_engine.py").read_bytes()
            ).hexdigest(),
            limitations=(
                "Synthetic equal-strength clubs, fresh lineups per match; "
                "no season injuries, suspensions, fatigue, transfers or MongoDB. "
                "Only one club adapts per paired season. Intervals use independent "
                "seed blocks and are exploratory, without multiple-comparison correction."
            ),
            dominance_rule=(
                "At least ten independent seeds; leader exceeds every alternative "
                "by >0.06 points/game at the lower approximate 95% paired interval bound"
            ),
        ),
        total_matches=len(seasons) * 760,
        strategy_points_per_game=summary,
        patterns=pattern_summary(strategy_samples),
        best_observed_strategy=leader,
        leader_differences=differences,
        dominant_strategy_detected=dominant,
        dominance_status="insufficient_seeds"
        if len(seeds) < 10
        else "exploratory_evidence"
        if dominant
        else "not_detected",
        adaptive_points_delta=interval(adaptive_by_seed),
        comparisons=comparisons,
        seasons=seasons,
    )


def render_report(report):
    """Readable summary; complete tables for every season remain in the JSON."""
    lines = [
        "# Calibração da Série A",
        "",
        f"{report['total_matches']:,} partidas; 20 clubes sintéticos de força 70, "
        "38 rodadas, nove estratégias e cenários fixos/pares com adaptação.",
        "",
        "## Estratégias fixas",
        "",
        "| Estratégia | Jogos | Vitórias | Empates | Derrotas | Pontos/jogo |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, summary in sorted(
        report["strategy_points_per_game"].items(), key=lambda item: -item[1]["mean"]
    ):
        rows = [
            row
            for pair in report["seasons"]
            for row in pair["fixed"]["table"]
            if row["initial_strategy"] == name
        ]
        totals = [sum(row[key] for row in rows) for key in ("games", "wins", "draws", "losses")]
        lines.append(f"| {name} | " + " | ".join(map(str, totals)) + f" | {summary['mean']:.4f} |")
    patterns = report["patterns"]
    effect = patterns["marking_vs_light"]["very_heavy"]
    bounds = effect["approximate_95_interval"]
    lines += ["", "### Padrão de marcação", ""]
    if patterns["very_heavy_best_in_each_style"]:
        lines.append("A marcação muito pesada teve a maior média nos três estilos testados.")
    lines.append(
        f"Vantagem média da marcação muito pesada contra a leve, "
        f"agrupando os estilos: {effect['mean']:+.4f} ponto/jogo."
    )
    if bounds:
        lines.append(f"Intervalo aproximado de 95%: [{bounds[0]:+.4f}, {bounds[1]:+.4f}].")
    lines.append(
        "Esse padrão merece acompanhamento; não implica uma combinação "
        "universalmente dominante e não inclui efeitos disciplinares entre rodadas."
    )
    status = report["dominance_status"]
    conclusion = {
        "not_detected": "Nenhuma estratégia atingiu o critério de dominância.",
        "insufficient_seeds": "Amostra insuficiente para o critério de dominância.",
        "exploratory_evidence": "A estratégia líder atingiu o critério exploratório.",
    }
    lines += [
        "",
        conclusion[status],
        "",
        "Critério: dez seeds ou mais; vantagem sobre todas as alternativas acima de "
        "0,06 ponto/jogo no limite inferior do intervalo aproximado de 95% por seed.",
        "",
        f"## Troca após {report['methodology']['bad_streak']} jogos sem vitória",
        "",
    ]
    delta = report["adaptive_points_delta"]
    bounds = delta["approximate_95_interval"]
    lines.append(f"Variação média do clube que troca: {delta['mean']:+.3f} pontos por temporada.")
    if bounds:
        lines.append(f"Intervalo aproximado de 95%: [{bounds[0]:+.3f}, {bounds[1]:+.3f}] pontos.")
    changes = sum(row["changes"] for row in report["comparisons"])
    lines += [
        f"Trocas realizadas: {changes}. Só um clube troca em cada comparação; "
        "os adversários mantêm suas estratégias.",
        "",
        "## Classificações do primeiro cenário",
        "",
        "As classificações abaixo exemplificam o primeiro par. O JSON contém os "
        "resultados de todos os clubes em todas as temporadas e o histórico de cada troca.",
    ]
    first = report["seasons"][0]
    for mode, title in (("fixed", "Estratégias fixas"), ("adaptive", "Com troca de estratégia")):
        season = first[mode]
        lines += [
            "",
            f"### {title} — seed {season['seed']}, rotação {season['rotation']}",
            "",
            "| Pos. | Clube | P | V | E | D | GP | GC | Estratégias utilizadas (jogos) |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
        for row in season["table"]:
            used = "; ".join(
                f"{name}: {stats['games']}" for name, stats in row["strategies_used"].items()
            )
            cells = [
                row[key]
                for key in (
                    "position",
                    "name",
                    "points",
                    "wins",
                    "draws",
                    "losses",
                    "goals_for",
                    "goals_against",
                )
            ]
            lines.append("| " + " | ".join(map(str, cells)) + f" | {used} |")
    lines += [
        "",
        "Limites: elencos reiniciados por partida, sem evolução de condição, "
        "lesões ou suspensões entre rodadas, mercado ou banco de dados. Intervalos exploratórios, "
        "sem correção para comparações múltiplas. A política de troca é cíclica; "
        "os resultados não demonstram o efeito de outras políticas.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=[35 + 100 * i for i in range(10)])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--bad-streak", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("docs/calibration-serie-a.json"))
    args = parser.parse_args()
    report = calibrate(args.seeds, args.bad_streak, args.workers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    args.output.with_suffix(".md").write_text(render_report(report))
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "total_matches",
                    "best_observed_strategy",
                    "dominance_status",
                    "adaptive_points_delta",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
