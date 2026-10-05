from dataclasses import dataclass


@dataclass(frozen=True)
class CupConfig:
    MAX_PARTICIPANTS: int = 128
    MAX_DIVISION_TIER: int = 4
    PHASE_PRIZE: int = 50_000
    CHAMPION_PRIZE: int = 1_000_000

    @classmethod
    def from_rules(cls, rules):
        return cls(
            **{key: value for key, value in rules.items() if key in cls.__dataclass_fields__}
        )

    def __post_init__(self):
        if (
            self.MAX_PARTICIPANTS < 2
            or self.MAX_DIVISION_TIER < 0
            or min(self.PHASE_PRIZE, self.CHAMPION_PRIZE) < 0
        ):
            raise ValueError("Invalid cup configuration")
