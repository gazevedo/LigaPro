"""Small, bounded performance modifiers and post-match morale rules."""

from dataclasses import dataclass
from math import isfinite


def band(value):
    return next((i for i, ceiling in enumerate((20, 40, 60, 80, 100)) if value <= ceiling), 4)


@dataclass(frozen=True)
class MoraleConfig:
    initial: int = 50
    factors: tuple = (0.94, 0.97, 1.00, 1.02, 1.04)
    victory: int = 3
    defeat: int = -3
    starting: int = 1
    goal: int = 2
    promotion: int = 5
    transfer: int = 3
    future_transfer: int = -2
    absence_threshold: int = 3

    def __post_init__(self):
        if len(self.factors) != 5 or any(
            not isfinite(x) or not 0.94 <= x <= 1.04 for x in self.factors
        ):
            raise ValueError("Morale modifiers must remain between 0.94 and 1.04")
        if not 0 <= self.initial <= 100 or self.absence_threshold < 1:
            raise ValueError("Invalid morale configuration")

    def modifier(self, value):
        return self.factors[band(max(0, min(100, value)))]


@dataclass(frozen=True)
class ChemistryConfig:
    initial: int = 40
    factors: tuple = (0.92, 0.96, 1.00, 1.02, 1.04)
    signing_loss: int = 5

    def __post_init__(self):
        if len(self.factors) != 5 or any(
            not isfinite(x) or not 0.92 <= x <= 1.04 for x in self.factors
        ):
            raise ValueError("Chemistry modifiers must remain between 0.92 and 1.04")
        if not 0 <= self.initial <= 100 or self.signing_loss < 0:
            raise ValueError("Invalid chemistry configuration")

    def modifier(self, value):
        return self.factors[band(max(0, min(100, value)))]
