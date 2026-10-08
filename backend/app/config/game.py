"""Competition and player rules; overrides live in app_settings.game_rules."""

from dataclasses import asdict, dataclass
from math import isfinite


@dataclass(frozen=True)
class GameConfig:
    TEAMS_PER_DIVISION: int = 20
    PRESEASON_DAYS: int = 2
    MIDSEASON_TRANSFER_WINDOW_DAYS: int = 2
    SEASON_DURATION_DAYS: int = 30
    PROMOTION_COUNT: int = 4
    RELEGATION_COUNT: int = 4
    INITIAL_SQUAD_SIZE: int = 25
    MAX_PLAYER_LEVEL: int = 100
    YOUTH_PLAYERS_PER_SEASON: int = 2
    MAX_YOUTH_PLAYERS: int = 20
    YOUTH_PROMOTION_AGE: int = 18
    PLAYER_DECLINE_AGE: int = 35
    BOT_REPLACEMENT_STRATEGY: str = "lowest_ranked"
    INITIAL_POSITION_COUNTS: tuple = (("GK", 3), ("DEF", 8), ("MID", 8), ("ATT", 6))
    DECLINE_PROBABILITIES: tuple = (
        (35, 0.10),
        (36, 0.15),
        (37, 0.20),
        (38, 0.30),
        (39, 0.40),
        (40, 0.50),
    )
    RETIREMENT_PROBABILITIES: tuple = (
        (35, 0.01),
        (36, 0.02),
        (37, 0.05),
        (38, 0.10),
        (39, 0.15),
        (40, 0.25),
        (41, 0.35),
        (42, 0.50),
    )
    ROUND_OFFSETS_DAYS: tuple = ()

    def __post_init__(self):
        integer_fields = (
            "TEAMS_PER_DIVISION",
            "PRESEASON_DAYS",
            "MIDSEASON_TRANSFER_WINDOW_DAYS",
            "SEASON_DURATION_DAYS",
            "PROMOTION_COUNT",
            "RELEGATION_COUNT",
            "INITIAL_SQUAD_SIZE",
            "MAX_PLAYER_LEVEL",
            "YOUTH_PLAYERS_PER_SEASON",
            "MAX_YOUTH_PLAYERS",
            "YOUTH_PROMOTION_AGE",
            "PLAYER_DECLINE_AGE",
        )
        if any(type(getattr(self, key)) is not int for key in integer_fields):
            raise ValueError("Integer game rules must be integers")
        if self.YOUTH_PROMOTION_AGE < 1 or self.PLAYER_DECLINE_AGE < 1:
            raise ValueError("Age thresholds must be positive")
        if self.TEAMS_PER_DIVISION != 20:
            raise ValueError("Each division must have twenty clubs")
        if not 0 < self.PROMOTION_COUNT <= 10 or not 0 < self.RELEGATION_COUNT <= 10:
            raise ValueError("Invalid promotion/relegation counts")
        if self.PROMOTION_COUNT != self.RELEGATION_COUNT:
            raise ValueError("Promotion and relegation must preserve division sizes")
        if self.SEASON_DURATION_DAYS <= self.PRESEASON_DAYS + self.MIDSEASON_TRANSFER_WINDOW_DAYS:
            raise ValueError("Season requires playing days")
        if self.PRESEASON_DAYS < 0 or self.MIDSEASON_TRANSFER_WINDOW_DAYS < 0:
            raise ValueError("Invalid transfer windows")
        if (
            self.INITIAL_SQUAD_SIZE != sum(n for _, n in self.INITIAL_POSITION_COUNTS)
            or dict(self.INITIAL_POSITION_COUNTS).keys() != {"GK", "DEF", "MID", "ATT"}
            or len(self.INITIAL_POSITION_COUNTS) != 4
            or any(type(n) is not int for _, n in self.INITIAL_POSITION_COUNTS)
            or any(
                dict(self.INITIAL_POSITION_COUNTS).get(position, 0) < minimum
                for position, minimum in (("GK", 1), ("DEF", 4), ("MID", 4), ("ATT", 2))
            )
        ):
            raise ValueError("Initial squad must support 4-4-2")
        if self.BOT_REPLACEMENT_STRATEGY not in {"lowest_ranked", "highest_ranked"}:
            raise ValueError("Unknown bot replacement strategy")
        if (
            not 1 <= self.MAX_PLAYER_LEVEL <= 100
            or self.YOUTH_PLAYERS_PER_SEASON < 0
            or self.MAX_YOUTH_PLAYERS < 2
        ):
            raise ValueError("Invalid player configuration")
        for probabilities in (self.DECLINE_PROBABILITIES, self.RETIREMENT_PROBABILITIES):
            if not probabilities or list(probabilities) != sorted(probabilities):
                raise ValueError("Age probabilities must be ordered")
            if any(not 0 <= probability <= 1 for _, probability in probabilities):
                raise ValueError("Invalid age probability")
            if any(b[1] < a[1] for a, b in zip(probabilities, probabilities[1:])):
                raise ValueError("Age probabilities must not decrease")
        offsets = self.round_offsets()
        midpoint = self.midseason_start
        if (
            len(offsets) != 38
            or list(offsets) != sorted(offsets)
            or any(
                not isfinite(d)
                or d < self.PRESEASON_DAYS
                or d >= self.SEASON_DURATION_DAYS
                or midpoint <= d < midpoint + self.MIDSEASON_TRANSFER_WINDOW_DAYS
                for d in offsets
            )
        ):
            raise ValueError("Round dates must fit outside transfer windows")

    @property
    def midseason_start(self):
        return self.SEASON_DURATION_DAYS / 2

    def round_offsets(self):
        if self.ROUND_OFFSETS_DAYS:
            return self.ROUND_OFFSETS_DAYS
        first_start = self.PRESEASON_DAYS
        second_start = self.midseason_start + self.MIDSEASON_TRANSFER_WINDOW_DAYS
        # Twenty rounds before the midseason window and eighteen after it:
        # two rounds per playing day, with twelve hours between kickoffs.
        return tuple(first_start + i / 2 for i in range(20)) + tuple(
            second_start + i / 2 for i in range(18)
        )

    @classmethod
    def from_rules(cls, rules):
        return cls(
            **{key: value for key, value in rules.items() if key in cls.__dataclass_fields__}
        )

    def snapshot(self):
        return asdict(self)


def legacy_position(position):
    return {"GK": "GOL", "CB": "DEF", "FB": "DEF", "MID": "MED", "ATT": "ATA"}.get(
        position, position
    )
