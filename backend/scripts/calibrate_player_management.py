"""Seeded calibration of pricing and physical condition using production rules.

Run with PYTHONPATH=backend and --output docs/player-management-calibration.json.
Prices are BRL; samples cover the market, not the narrower initial-squad distribution.
"""

import argparse
import json
from collections import Counter
from dataclasses import replace
from pathlib import Path
from random import Random

from calibrate_match_engine import make_team

from app.services.market_value import MarketValueService
from app.services.match_engine import MatchEngine
from app.services.salary import SalaryService


def prices(count=10000):
    rng = Random(210025)
    service = MarketValueService()
    values, salaries = [], []
    for _ in range(count):
        band = rng.random()
        # Ordinary players dominate; a small, explicit elite tail tests the top curve.
        strength = (
            rng.randint(40, 65)
            if band < 0.8
            else rng.randint(66, 82)
            if band < 0.985
            else rng.randint(90, 100)
        )
        player = {
            "strength": strength,
            "age": rng.randint(18, 35),
            "position": rng.choice(["GK", "FB", "CB", "MID", "ATT"]),
            "stars": 0,
        }
        values.append(service.calculate(player, club={"reputation": 30, "division_tier": 0}) / 100)
        salaries.append(SalaryService.reference(player) / 100)
    values.sort()
    return {
        "samples": count,
        "currency": "BRL",
        "median": values[count // 2],
        "p90": values[int(count * 0.90)],
        "p99": values[int(count * 0.99)],
        "average_salary": round(sum(salaries) / count, 2),
        "distribution": "80% strength 40–65, 18.5% 66–82, 1.5% 90–100; age 18–35; stars 0",
    }


def injuries(count=10000):
    groups = {}
    severity = Counter()
    durations = []
    engine = MatchEngine()
    for index in range(count):
        condition = (100, 80, 60, 35)[index % 4]
        age = 22 if index % 8 < 4 else 36
        home, away = make_team("h"), make_team("a")
        for squad in [home, away]:
            squad.lineup = [replace(p, age=age, physical_condition=condition) for p in squad.lineup]
        result = engine.simulate(home, away, index, capture_snapshot=False)
        events = [e for e in result["events"] if e["type"] == "injury"]
        key = f"condition_{condition}_age_{age}"
        group = groups.setdefault(key, {"matches": 0, "injuries": 0})
        group["matches"] += 1
        group["injuries"] += len(events)
        severity.update(e["severity"] for e in events)
        durations.extend(e["matches_out"] for e in events)
    for group in groups.values():
        group["injuries_per_match"] = round(group["injuries"] / group["matches"], 4)
    return {
        "matches": count,
        "groups": groups,
        "severity": dict(severity),
        "injuries_per_match": round(sum(severity.values()) / count, 4),
        "mean_matches_out": round(sum(durations) / max(1, len(durations)), 3),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {"seed": 210025, "pricing": prices(), "physical": injuries()}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
