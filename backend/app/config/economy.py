"""Economia inspirada no Brasfoot, com escala e periodicidade próprias.

Amounts are integer centavos, as in the existing API/mobile contract.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EconomyConfig:
    STARTING_CASH: int = 10_000_000
    MONTHLY_SPONSORSHIP: int = 500_000
    MONTHLY_TV_REVENUE: int = 1_000_000
    INITIAL_PAYROLL_TARGET_PERCENT: float = 0.90
    PAYROLL_TOLERANCE: float = 0.03
    POSITION_PRIZES: tuple = (
        80000,
        40000,
        20000,
        18000,
        17000,
        16000,
        15000,
        14000,
        13000,
        12000,
        11000,
        10000,
        9000,
        8000,
        7000,
        6000,
        5000,
        5000,
        5000,
        5000,
    )
    DIVISION_PRIZE_MULTIPLIERS: tuple = (1.0, 0.75, 0.55, 0.40, 0.30)
    ALLOW_NEGATIVE_CASH: bool = True

    @property
    def fixed_revenue(self):
        return self.MONTHLY_SPONSORSHIP + self.MONTHLY_TV_REVENUE

    @property
    def payroll_target(self):
        return round(self.fixed_revenue * self.INITIAL_PAYROLL_TARGET_PERCENT)

    def prize(self, position, tier):
        return round(
            self.POSITION_PRIZES[position - 1] * 100 * self.DIVISION_PRIZE_MULTIPLIERS[min(tier, 4)]
        )

    @classmethod
    def from_rules(cls, rules):
        return cls(
            **{key: value for key, value in rules.items() if key in cls.__dataclass_fields__}
        )

    def __post_init__(self):
        if (
            self.STARTING_CASH < 0
            or min(self.MONTHLY_SPONSORSHIP, self.MONTHLY_TV_REVENUE) < 0
            or not 0 < self.INITIAL_PAYROLL_TARGET_PERCENT <= 1
            or not 0 <= self.PAYROLL_TOLERANCE < 1
        ):
            raise ValueError("Invalid economy configuration")
        if (
            len(self.POSITION_PRIZES) != 20
            or len(self.DIVISION_PRIZE_MULTIPLIERS) != 5
            or min(self.POSITION_PRIZES) < 0
            or min(self.DIVISION_PRIZE_MULTIPLIERS) <= 0
        ):
            raise ValueError("Invalid prizes")


def salary_weight(player):
    strength = player.get("strength", player.get("overall", 50))
    position = {
        "GK": 1.0,
        "GOL": 1.0,
        "DEF": 0.95,
        "CB": 0.95,
        "FB": 0.95,
        "MID": 1.05,
        "MED": 1.05,
        "ATT": 1.15,
        "ATA": 1.15,
    }.get(player["position"], 1.0)
    return (
        max(1, strength)
        * position
        * max(0.7, 1 - abs(player["age"] - 27) * 0.015)
        * (1 + 0.1 * player.get("stars", 0))
    )


def payroll_health(payroll, fixed):
    ratio = payroll / fixed if fixed else float("inf")
    return (
        "saudável"
        if ratio <= 0.8
        else "atenção"
        if ratio <= 1
        else "alto risco"
        if ratio <= 1.2
        else "crítico"
    )
