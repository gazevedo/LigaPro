"""Salary reference is distinct from negotiated salary and market price."""

from app.config.economy import EconomyConfig


def interpolate(value, curve):
    if value <= curve[0][0]:
        return curve[0][1]
    for (low, a), (high, b) in zip(curve, curve[1:]):
        if value <= high:
            return a + (b - a) * (value - low) / (high - low)
    return curve[-1][1]


class SalaryService:
    CURVE = (
        (20, 150),
        (30, 220),
        (40, 320),
        (50, 450),
        (60, 650),
        (70, 900),
        (80, 1250),
        (90, 1700),
        (100, 2300),
    )

    @classmethod
    def reference(cls, player):
        strength = player.get("strength", player.get("overall", 50))
        age = player["age"]
        age_factor = 1.0 if age <= 28 else 0.95 if age <= 34 else 0.85
        position = {
            "GK": 0.95,
            "GOL": 0.95,
            "FB": 0.98,
            "CB": 1.0,
            "DEF": 1.0,
            "MID": 1.05,
            "MED": 1.05,
            "ATT": 1.10,
            "ATA": 1.10,
        }.get(player["position"], 1)
        stars = (1, 1.05, 1.10, 1.18, 1.28, 1.40)[max(0, min(5, player.get("stars", 0)))]
        return round(interpolate(strength, cls.CURVE) * 100 * age_factor * position * stars)

    @classmethod
    def normalize(cls, players, config=None):
        config = config or EconomyConfig()
        if not players:
            return []
        raw = [cls.reference(p) for p in players]
        target = round(config.payroll_target * len(players) / 25)
        salaries = [round(value * target / sum(raw)) for value in raw]
        salaries[-1] += target - sum(salaries)
        return salaries

    @classmethod
    def refresh(cls, repo, players):
        for player in players:
            repo.update(
                "players",
                {"_id": player["_id"]},
                {"$set": {"salary_reference": cls.reference(player)}},
            )
