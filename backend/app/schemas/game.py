from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClubInput(Input):
    name: str = Field(min_length=3, max_length=60)
    country_id: str = Field(min_length=2, max_length=3)
    badge_id: str = Field(min_length=1, max_length=40)

    @field_validator("name")
    @classmethod
    def name_valid(cls, value):
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Nome deve ter ao menos 3 caracteres")
        return value


class LineupInput(Input):
    formation: str
    starters: list[str] = Field(min_length=11, max_length=11)
    reserves: list[str]


class MoneyInput(Input):
    amount: int = Field(gt=0, le=1_000_000_000, strict=True)


class TicketInput(Input):
    price: int = Field(ge=0, le=100_000, strict=True)


class ListingInput(Input):
    player_id: str
    type: Literal["sale", "loan"]
    price: int = Field(gt=0, le=1_000_000_000, strict=True)
    duration_days: int = Field(default=30, ge=1, le=365, strict=True)


class OfferInput(MoneyInput):
    listing_id: str


class CalendarFilter(Input):
    start: datetime | None = None
    end: datetime | None = None
    type: (
        Literal[
            "match",
            "training",
            "competition",
            "transfer",
            "financial",
            "stadium",
            "other",
            "league_match",
            "cup_match",
            "friendly",
            "transfer_window_open",
            "transfer_window_close",
            "season_start",
            "season_end",
            "youth_generation",
            "financial_close",
            "training_event",
        ]
        | None
    ) = None

    @field_validator("start", "end")
    @classmethod
    def utc_dates(cls, value):
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("Informe a data com fuso horário ISO 8601")
            return value.astimezone(timezone.utc)
        return value


class TacticsInput(Input):
    formation: Literal["4-4-2", "4-3-3", "4-2-3-1", "3-5-2", "5-3-2", "4-5-1", "3-4-3"] = "4-4-2"
    play_style: Literal["balanced", "all_out_attack", "counter_attack"] = "balanced"
    marking: Literal["light", "heavy", "very_heavy"] = "light"
    attack_focus: Literal["normal", "center", "wings"] = "normal"


class MatchCommandInput(Input):
    minute: int = Field(ge=0, le=85, strict=True)
    type: Literal["tactics_change", "substitution"]
    payload: dict


class PlayerContractInput(Input):
    salary: int = Field(gt=0, le=1_000_000_000, strict=True)
    seasons: int = Field(ge=1, le=5, strict=True)


class TrainingInput(Input):
    skill: (
        Literal[
            "goalkeeping", "speed", "technique", "passing", "tackling", "playmaking", "finishing"
        ]
        | None
    ) = None


class NegotiationInput(Input):
    player_id: str
    offer_type: Literal["sale", "loan"] = "sale"
    transfer_value: int = Field(ge=0, le=1_000_000_000, strict=True)
    salary_offer: int = Field(gt=0, le=1_000_000_000, strict=True)
    contract_months: int = Field(default=24, ge=1, le=60, strict=True)
    loan_months: int = Field(default=6, ge=1, le=12, strict=True)
    salary_share: float = Field(default=0.5, ge=0, le=1)
    expected_starter: bool = True


class CounterOfferInput(Input):
    transfer_value: int = Field(ge=0, le=1_000_000_000, strict=True)
    salary_offer: int | None = Field(default=None, gt=0, le=1_000_000_000, strict=True)
    contract_months: int | None = Field(default=None, ge=1, le=60, strict=True)
    loan_months: int | None = Field(default=None, ge=1, le=12, strict=True)
    salary_share: float | None = Field(default=None, ge=0, le=1)


class TransferStatusInput(Input):
    status: Literal["available", "not_for_sale"]


class FriendlyInput(Input):
    opponent_club_id: str
    date: datetime

    @field_validator("date")
    @classmethod
    def utc_date(cls, value):
        if value.tzinfo is None:
            raise ValueError("Informe o fuso horário")
        return value.astimezone(timezone.utc)
