from dataclasses import dataclass


@dataclass(frozen=True)
class PhysicalConfig:
    factors: tuple = ((39, 0.84), (54, 0.90), (69, 0.95), (84, 0.98), (100, 1.0))
    recovery_per_day: float = 20
    medical_bonus: float = 2
    injury_probability: float = 0.0015
    severity_weights: tuple = (0.75, 0.22, 0.03)

    def modifier(self, value):
        return next(factor for ceiling, factor in self.factors if value <= ceiling)

    def risk(self, condition, age, marking="light", dangerous=False, minutes=90):
        fatigue = max(0, 85 - condition) / 30
        age_factor = 1 + max(0, age - 28) * 0.04
        intensity = {"light": 1, "heavy": 1.2, "very_heavy": 1.5}[marking]
        return min(
            0.08,
            self.injury_probability
            * (1 + fatigue**1.5)
            * age_factor
            * intensity
            * (2 if dangerous else 1)
            * minutes
            / 90,
        )
