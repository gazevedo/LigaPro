from dataclasses import dataclass


@dataclass(frozen=True)
class MarketValueConfig:
    strength_curve: tuple = (
        (20, 500),
        (30, 1000),
        (40, 2500),
        (50, 6000),
        (60, 12000),
        (70, 22000),
        (80, 40000),
        (90, 70000),
        (100, 100000),
    )
    age_factors: tuple = (
        (20, 1.20),
        (24, 1.15),
        (28, 1.05),
        (31, 0.95),
        (34, 0.80),
        (37, 0.65),
        (200, 0.50),
    )
    stars_factors: tuple = (1, 1.05, 1.10, 1.18, 1.28, 1.40)
    position_factors: tuple = (
        ("GK", 0.95),
        ("GOL", 0.95),
        ("FB", 0.98),
        ("CB", 1),
        ("DEF", 1),
        ("MID", 1.05),
        ("MED", 1.05),
        ("ATT", 1.10),
        ("ATA", 1.10),
    )
    division_factors: tuple = (1, 0.92, 0.84, 0.76, 0.68)
    minimum: int = 50_000
    maximum: int = 12_000_000
