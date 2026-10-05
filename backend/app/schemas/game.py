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
        Literal["match", "training", "competition", "transfer", "financial", "stadium", "other"]
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
