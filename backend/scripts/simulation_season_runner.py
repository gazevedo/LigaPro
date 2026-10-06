"""Persistent seeded universes, full 38-round leagues, production match engine.

Scales count completed seasons across seeds (default four independent universes).
Mongo transactions, cup, human actions and negotiation acceptance are outside this
in-memory stress model and explicitly reported as limitations, not simulated.
"""

import argparse
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from math import ceil
from pathlib import Path
from random import Random
from statistics import mean

from app.config.economy import EconomyConfig
from app.config.game import GameConfig
from app.models.game import DEFAULT_RULES
from app.services.bank_loans import PRODUCTS
from app.services.career_development import CareerDevelopmentService
from app.services.competition import movement, ranked, round_robin
from app.services.fan_base import FanBaseService
from app.services.market_value import MarketValueService
from app.services.match_engine import MatchEngine, MatchPlayer, MatchTeam, arrange_formation
from app.services.physical_condition import PhysicalConditionService
from app.services.player_development import PlayerAgingService, PlayerGeneratorService
from app.services.salary import SalaryService
from app.services.sponsorship import SponsorshipService


def percentile(values, fraction):
    values = sorted(values)
    return values[min(len(values) - 1, max(0, ceil(len(values) * fraction) - 1))] if values else 0


def run_universe(seed, checkpoints):
    rng = Random(seed)
    generator = PlayerGeneratorService(seed=seed)
    economy, rules = EconomyConfig(), GameConfig()
    engine, physical, pricing = MatchEngine(), PhysicalConditionService(), MarketValueService()
    clubs = []
    for i in range(40):
        players = generator.squad(str(i), "BR")
        for j, p in enumerate(players):
            p["_id"] = f"{i}-{j}"
            p["salary"] = SalaryService.normalize(players)[j]
            p.update(
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                condition_updated_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        clubs.append(
            {
                "_id": str(i),
                "division_tier": i // 20,
                "reputation": 10,
                "supporters": 1000,
                "fan_satisfaction": 50,
                "result_streak": 0,
                "cash": economy.STARTING_CASH,
                "players": players,
                "youth": [],
                "loans": [],
                "serial": 25,
            }
        )
    metrics = []
    previous_champion = None
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for season in range(max(checkpoints)):
        now = start + timedelta(days=30 * season)
        tables = {
            tier: [
                {
                    "_id": c["_id"],
                    "club_id": c["_id"],
                    "points": 0,
                    "goals_for": 0,
                    "goal_difference": 0,
                    "wins": 0,
                }
                for c in clubs
                if c["division_tier"] == tier
            ]
            for tier in range(2)
        }
        table_rows = {r["club_id"]: r for table in tables.values() for r in table}
        stats = Counter()
        revenues, salaries, gates, sponsors, prizes, transfer_fees = [], [], [], [], [], []
        for club in clubs:
            # Two youth entries per season, bounded academy, with legal promotions.
            incoming = generator.youth(club["_id"], "BR")[: max(0, 20 - len(club["youth"]))]
            for p in incoming:
                p.update(created_at=now, condition_updated_at=now)
            club["youth"] += incoming
            stats["youth_entries"] += len(incoming)
            for p in list(club["youth"]):
                if p["age"] >= 18 and len(club["players"]) < 25:
                    club["serial"] += 1
                    p.update(
                        _id=f"{club['_id']}-{club['serial']}", salary=SalaryService.reference(p)
                    )
                    club["players"].append(p)
                    club["youth"].remove(p)
                    stats["youth_promotions"] += 1
            # Free agents fill only positional shortages, as a roster fallback.
            targets = {"GK": 3, "FB": 4, "CB": 4, "MID": 8, "ATT": 6}
            for role, target in targets.items():
                existing = sum(p["position"] == role for p in club["players"])
                while existing < target and len(club["players"]) < 25:
                    p = generator.player(club["_id"], "BR", role)
                    p.update(created_at=now, condition_updated_at=now)
                    club["serial"] += 1
                    p.update(
                        _id=f"{club['_id']}-{club['serial']}", salary=SalaryService.reference(p)
                    )
                    club["players"].append(p)
                    existing += 1
                    stats["free_agent_entries"] += 1
            if season and season % 3 == 0:
                for p in club["players"]:
                    p["salary"] = SalaryService.reference(p)
            monthly_sponsor = (
                economy.MONTHLY_SPONSORSHIP
                if not season
                else round(SponsorshipService.value(club) * 1.05)
            )
            payroll = sum(p["salary"] for p in club["players"])
            sponsor_income = monthly_sponsor * 12
            revenues.append(sponsor_income + economy.MONTHLY_TV_REVENUE * 12)
            sponsors.append(sponsor_income)
            salaries.append(payroll * 12)
            for month in range(12):
                club["cash"] += monthly_sponsor + economy.MONTHLY_TV_REVENUE - payroll
                for loan in list(club["loans"]):
                    payment = min(loan["installment"], loan["remaining"])
                    if club["cash"] < payment:
                        loan["overdue"] = True
                        continue
                    club["cash"] -= payment
                    loan["remaining"] -= payment
                    loan["overdue"] = False
                    if not loan["remaining"]:
                        club["loans"].remove(loan)
                if club["cash"] < payroll and not club["loans"]:
                    limit = min(
                        DEFAULT_RULES["max_bank_loan"],
                        2 * (monthly_sponsor + economy.MONTHLY_TV_REVENUE)
                        + max(0, club["cash"]) // 10
                        + club["reputation"] * 100,
                    )
                    principal = max(0, min(payroll - club["cash"], limit))
                    if principal:
                        terms = PRODUCTS["short_term"]
                        total = principal + round(principal * terms["interest_rate"])
                        club["loans"].append(
                            {
                                "remaining": total,
                                "installment": ceil(total / terms["installments"]),
                                "overdue": False,
                            }
                        )
                        club["cash"] += principal
                        stats["credit_contracts"] += 1
        # Limited transfers between bots; fee conserves total club cash.
        for _ in range(20):
            seller, buyer = rng.sample(clubs, 2)
            if len(seller["players"]) <= 22:
                continue
            p = min(seller["players"], key=lambda p: p["strength"])
            fee = pricing.calculate(p, club=seller)
            payroll = sum(p["salary"] for p in buyer["players"])
            if (
                len(buyer["players"]) >= 27
                or buyer["cash"] - max(2 * payroll, economy.fixed_revenue) < fee
                or payroll + p["salary"] > economy.fixed_revenue * 1.2
            ):
                continue
            seller["players"].remove(p)
            buyer["players"].append(p)
            seller["cash"] += fee
            buyer["cash"] -= fee
            transfer_fees.append(fee)
        rounds = {
            tier: round_robin([r["club_id"] for r in table]) for tier, table in tables.items()
        }
        for round_no in range(38):
            date = now + timedelta(days=rules.round_offsets()[round_no])
            teams = {}
            for club in clubs:
                available = []
                for p in club["players"]:
                    p.update(physical.recover(p, date))
                    if p.get("unavailable_round", -1) >= round_no:
                        continue
                    available.append(p)
                selected = []
                for role, count in {"GK": 1, "FB": 2, "CB": 2, "MID": 4, "ATT": 2}.items():
                    selected += sorted(
                        [p for p in available if p["position"] == role],
                        key=lambda p: (
                            -(
                                p["strength"]
                                * (0.7 + 0.3 * p["physical_condition"] / 100)
                                * (0.7 + 0.3 * p["energy"] / 100)
                            )
                        ),
                    )[:count]
                if len(selected) < 11:
                    selected += sorted(
                        [p for p in available if p not in selected], key=lambda p: -p["strength"]
                    )[: 11 - len(selected)]
                if len(selected) < 11 or not any(p["position"] == "GK" for p in selected):
                    teams[club["_id"]] = None
                    stats["invalid_lineups"] += 1
                    continue
                reserves = [p for p in available if p not in selected]
                teams[club["_id"]] = MatchTeam(
                    club["_id"],
                    arrange_formation([MatchPlayer.from_document(p) for p in selected], "4-4-2"),
                    "4-4-2",
                    "balanced",
                    "light",
                    "normal",
                    reserves=[MatchPlayer.from_document(p) for p in reserves],
                    is_bot=True,
                )
                stats["lineup_quality_sum"] += mean(p["strength"] for p in selected)
                stats["lineup_quality_count"] += 1
            for tier in range(2):
                for h, a in rounds[tier][round_no]:
                    home, away = clubs[int(h)], clubs[int(a)]
                    if teams[h] and teams[a]:
                        result = engine.simulate(
                            teams[h],
                            teams[a],
                            seed * 100000000
                            + season * 1000
                            + tier * 380
                            + round_no * 10
                            + rounds[tier][round_no].index((h, a)),
                            capture_snapshot=False,
                        )
                        hg, ag = result["score"][h], result["score"][a]
                        for event in result["events"]:
                            stats[event["type"]] += 1
                            if event["type"] in {"injury", "red_card"}:
                                c = clubs[int(event["team_id"])]
                                for p in c["players"]:
                                    if str(p["_id"]) == event.get("player_id"):
                                        p["unavailable_round"] = round_no + (
                                            event.get("matches_out", 1)
                                            if event["type"] == "injury"
                                            else 1
                                        )
                        for c, team in [(home, teams[h]), (away, teams[a])]:
                            active = {p.id for p in team.lineup}
                            for p in c["players"]:
                                if str(p["_id"]) in active:
                                    p["energy"] = max(0, p["energy"] - 27)
                                    p["physical_condition"] = max(
                                        0, p["physical_condition"] - physical.wear(p, 90)
                                    )
                                    p["season_minutes"] = p.get("season_minutes", 0) + 90
                    else:
                        hg, ag = (3 if teams[h] else 0), (3 if teams[a] else 0)
                        stats["walkovers"] += 1
                    stats["matches"] += 1
                    stats["goals"] += hg + ag
                    stats["draws"] += hg == ag
                    stats["home_wins"] += hg > ag
                    strong = mean(p["strength"] for p in home["players"]) > mean(
                        p["strength"] for p in away["players"]
                    )
                    stats["stronger_wins"] += hg > ag if strong else ag > hg
                    for c, scored, conceded in [(home, hg, ag), (away, ag, hg)]:
                        row = table_rows[c["_id"]]
                        row["points"] += 3 if scored > conceded else 1 if scored == conceded else 0
                        row["goals_for"] += scored
                        row["goal_difference"] += scored - conceded
                        row["wins"] += scored > conceded
                        c["result_streak"] = (
                            max(0, c["result_streak"]) + 1
                            if scored > conceded
                            else min(0, c["result_streak"]) - 1
                            if scored < conceded
                            else 0
                        )
                        c["fan_satisfaction"] = max(
                            0,
                            min(
                                100,
                                c["fan_satisfaction"]
                                + (3 if scored > conceded else -3 if scored < conceded else 0),
                            ),
                        )
                    gate = (
                        FanBaseService.attendance(
                            home, {"capacity": 1000, "ticket_price": 2000}, opponent=away
                        )
                        * 2000
                    )
                    home["cash"] += gate
                    gates.append(gate)
        tables = {tier: ranked(rows) for tier, rows in tables.items()}
        destinations = movement(tables, rules)
        champion = tables[0][0]["club_id"]
        stats["champion_repeat"] = champion == previous_champion
        previous_champion = champion
        for tier, rows in tables.items():
            for position, row in enumerate(rows, 1):
                c = clubs[int(row["club_id"])]
                prize = economy.prize(position, tier)
                c["cash"] += prize
                prizes.append(prize)
                stats["promotions"] += destinations[c["_id"]] < tier
                stats["relegations"] += destinations[c["_id"]] > tier
                c["division_tier"] = destinations[c["_id"]]
                c["reputation"] = max(
                    0,
                    min(100, c["reputation"] + (3 if position < 5 else -2 if position > 16 else 0)),
                )
        for c in clubs:
            for p in list(c["players"]):
                old = p["strength"]
                values, _ = CareerDevelopmentService.evolve(p, rng, p.pop("season_minutes", 0), 76)
                age = values["age"]
                if age >= rules.PLAYER_DECLINE_AGE:
                    if rng.random() < PlayerAgingService.probability(
                        age, rules.DECLINE_PROBABILITIES
                    ):
                        values["strength"] = max(1, old - 1)
                    values["retired"] |= rng.random() < PlayerAgingService.probability(
                        age, rules.RETIREMENT_PROBABILITIES
                    )
                p.update(values)
                p.pop("unavailable_round", None)
                stats["development"] += p["strength"] > old
                stats["regression"] += p["strength"] < old
                if values["retired"]:
                    c["players"].remove(p)
                    stats["retirements"] += 1
            for p in list(c["youth"]):
                values, _ = CareerDevelopmentService.evolve(
                    p, rng, 0, 76, ceiling=p["estimated_potential_capacity"]
                )
                p.update(values)
                if p["age"] > 21:
                    c["youth"].remove(p)
        players = [p for c in clubs for p in c["players"]]
        prices = [pricing.calculate(p, club=c) for c in clubs for p in c["players"]]
        cash = [c["cash"] for c in clubs]
        metrics.append(
            {
                "seed": seed,
                "season": season + 1,
                "matches": stats["matches"],
                "goals_per_match": stats["goals"] / stats["matches"],
                "draw_rate": stats["draws"] / stats["matches"],
                "home_win_rate": stats["home_wins"] / stats["matches"],
                "cards_per_match": (stats["yellow_card"] + stats["red_card"]) / stats["matches"],
                "injuries_per_match": stats["injury"] / stats["matches"],
                "stronger_win_rate": stats["stronger_wins"] / stats["matches"],
                "cash_mean": mean(cash),
                "cash_p90": percentile(cash, 0.9),
                "cash_p10": percentile(cash, 0.1),
                "revenue_mean": (sum(revenues) + sum(gates) + sum(prizes)) / 40,
                "payroll_mean": mean(salaries),
                "debt_mean": sum(loan["remaining"] for c in clubs for loan in c["loans"]) / 40,
                "prizes_mean": mean(prizes),
                "ticketing_mean": sum(gates) / 40,
                "sponsorship_mean": mean(sponsors),
                "transfer_volume": len(transfer_fees),
                "transfer_value": sum(transfer_fees),
                "market_median": percentile(prices, 0.5),
                "market_p90": percentile(prices, 0.9),
                "market_p99": percentile(prices, 0.99),
                "talent_concentration": max(sum(p["strength"] for p in c["players"]) for c in clubs)
                / sum(p["strength"] for p in players),
                "strength_mean": mean(p["strength"] for p in players),
                "strength_p99": percentile([p["strength"] for p in players], 0.99),
                "age_mean": mean(p["age"] for p in players),
                "elite_share": mean(p["strength"] >= 90 for p in players),
                "bankrupt_share": mean(v < 0 for v in cash),
                "cash_inequality": (max(cash) - min(cash)) / max(1, abs(mean(cash))),
                "lineup_quality": stats["lineup_quality_sum"]
                / max(1, stats["lineup_quality_count"]),
                **{
                    key: stats[key]
                    for key in [
                        "development",
                        "regression",
                        "retirements",
                        "youth_entries",
                        "youth_promotions",
                        "free_agent_entries",
                        "promotions",
                        "relegations",
                        "champion_repeat",
                        "walkovers",
                        "credit_contracts",
                    ]
                },
            }
        )
        if (season + 1) % 10 == 0:
            print(f"seed {seed}: {season + 1}/{max(checkpoints)} seasons", flush=True)
    return metrics


def report(universes, scales, seeds):
    reports = []
    for scale in scales:
        rows = [
            r
            for i, universe in enumerate(universes)
            for r in universe[: scale // len(seeds) + int(i < scale % len(seeds))]
        ]
        keys = [k for k in rows[0] if k not in {"seed", "season"}]
        summary = {
            key: {
                "mean": mean(r[key] for r in rows),
                "p10": percentile([r[key] for r in rows], 0.1),
                "p50": percentile([r[key] for r in rows], 0.5),
                "p90": percentile([r[key] for r in rows], 0.9),
                "p99": percentile([r[key] for r in rows], 0.99),
            }
            for key in keys
        }
        alerts = []
        for key, low, high in [
            ("draw_rate", 0.12, 0.35),
            ("injuries_per_match", 0, 0.3),
            ("elite_share", 0, 0.1),
            ("champion_repeat", 0, 0.6),
            ("bankrupt_share", 0, 0.1),
        ]:
            if not low <= summary[key]["mean"] <= high:
                alerts.append(f"{key} outside [{low}, {high}]: {summary[key]['mean']:.3f}")
        first = [u[0] for u in universes]
        last = [
            u[min(len(u), scale // len(seeds) + int(i < scale % len(seeds))) - 1]
            for i, u in enumerate(universes)
        ]
        inflation = mean(r["market_median"] for r in last) / max(
            1, mean(r["market_median"] for r in first)
        )
        revenue_growth = mean(r["revenue_mean"] for r in last) / max(
            1, mean(r["revenue_mean"] for r in first)
        )
        if inflation > revenue_growth * 1.2:
            alerts.append("Market prices growing faster than revenue")
        growth = mean(r["cash_mean"] for r in last) / max(1, mean(r["cash_mean"] for r in first))
        # Compare cumulative wealth against a linear per-season revenue envelope.
        if growth > 1 + max(r["season"] for r in last) * 2 * revenue_growth:
            alerts.append("Cash exceeds linear growth envelope: investigate exponential growth")
        reports.append(
            {
                "completed_seasons": len(rows),
                "matches": sum(r["matches"] for r in rows),
                "seeds": seeds,
                "metrics": summary,
                "price_inflation_factor": inflation,
                "revenue_growth_factor": revenue_growth,
                "alerts": alerts,
                "recommendations": [
                    "Measure a candidate rule change with paired seeds before changing production configuration."  # noqa: E501
                ]
                + (
                    [
                        "Investigate alerted metrics with transaction-backed integration seasons; do not tune from this model alone."  # noqa: E501
                    ]
                    if alerts
                    else []
                ),
            }
        )
    return {
        "methodology": "All 38 rounds / 20 clubs / two divisions; production MatchEngine, career, salary, attendance, sponsor, market valuation and movement rules. Scales are pooled season counts across independent persistent seeded universes.",  # noqa: E501
        "currency_unit": "integer centavos",
        "limitations": [
            "Supporter counts and stadium capacity are held fixed; supporter growth and stadium ROI are covered by service tests, not this stress model.",  # noqa: E501
            "In-memory stress model excludes Mongo transaction behavior, cup income, stadium expansions and human decisions.",  # noqa: E501
            "Market acceptance and cash-flow timing are simplified: bounded cash-conserving transfers, annual 12-month accounting, free-agent positional replacement; not the complete BotManager negotiation loop.",  # noqa: E501
            "Injuries and red-card absence are measured from the engine; physical consequences use starter wear. Bench minutes and match ratings are not propagated in this stress model.",  # noqa: E501
        ],
        "scales": reports,
        "series": universes,
    }


def write_reports(data, output):
    output.mkdir(parents=True, exist_ok=True)
    (output / "balance_report.json").write_text(json.dumps(data, indent=2) + "\n")
    lines = [
        "# Global balance measurement",
        "",
        data["methodology"],
        "",
        "## Limits",
        "",
        *[f"- {s}" for s in data["limitations"]],
    ]
    for scale in data["scales"]:
        lines += [
            "",
            f"## {scale['completed_seasons']} seasons · {scale['matches']} matches",
            "",
            "Metric | Mean | P50 | P90 | P99",
            "--- | ---: | ---: | ---: | ---:",
        ]
        lines += [
            f"{key} | {v['mean']:.3f} | {v['p50']:.3f} | {v['p90']:.3f} | {v['p99']:.3f}"
            for key, v in scale["metrics"].items()
        ]
        lines += [
            "",
            "Alerts:",
            *[f"- {a}" for a in scale["alerts"] or ["None in measured bands."]],
            "",
            *scale["recommendations"],
        ]
    lines += [
        "",
        "![Cash evolution](balance_cash.svg)",
        "",
        "![Strength evolution](balance_strength.svg)",
    ]
    (output / "balance_report.md").write_text("\n".join(lines) + "\n")
    for metric, name in [("cash_mean", "cash"), ("strength_mean", "strength")]:
        values = [row[metric] for universe in data["series"] for row in universe]
        low, high = min(values), max(values)
        palette = ["#2563eb", "#dc2626", "#059669", "#9333ea"]
        paths = []
        for i, universe in enumerate(data["series"]):
            points = " ".join(
                f"{40 + 700 * j / max(1, len(universe) - 1):.1f},{240 - 190 * (r[metric] - low) / max(1, high - low):.1f}"  # noqa: E501
                for j, r in enumerate(universe)
            )
            paths.append(
                f'<polyline points="{points}" fill="none" stroke="{palette[i % 4]}" stroke-width="2"/>'  # noqa: E501
            )
        (output / f"balance_{name}.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="280" viewBox="0 0 800 280"><rect width="800" height="280" fill="white"/><text x="40" y="25">{metric} · {low:.0f}–{high:.0f} · per seed</text><path d="M40 45 V240 H750" fill="none" stroke="black"/>{"".join(paths)}<text x="40" y="268">Season 1 → {max(map(len, data["series"]))}</text></svg>'  # noqa: E501
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scales", type=int, nargs="+", default=[10, 100, 1000])
    parser.add_argument("--seeds", type=int, nargs="+", default=[35, 135, 235, 335])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path("reports/global-balance"))
    args = parser.parse_args()
    if min(args.scales) < len(args.seeds) or len(set(args.seeds)) != len(args.seeds):
        parser.error("Scales must include each distinct seed at least once")
    universes = [None] * len(args.seeds)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs = {
            pool.submit(
                run_universe,
                seed,
                [s // len(args.seeds) + int(i < s % len(args.seeds)) for s in args.scales],
            ): i
            for i, seed in enumerate(args.seeds)
        }
        for job in as_completed(jobs):
            universes[jobs[job]] = job.result()
    data = report(universes, args.scales, args.seeds)
    write_reports(data, args.output)
    print(
        json.dumps(
            {
                "scales": [
                    {
                        "seasons": s["completed_seasons"],
                        "matches": s["matches"],
                        "alerts": s["alerts"],
                    }
                    for s in data["scales"]
                ]
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
