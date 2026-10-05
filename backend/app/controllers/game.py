from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_user
from app.database.mongo import get_database
from app.repositories.game import GameRepository
from app.schemas.game import (
    CalendarFilter,
    ClubInput,
    LineupInput,
    ListingInput,
    MoneyInput,
    OfferInput,
    TicketInput,
)
from app.services.competition import CompetitionService
from app.services.game import (
    CalendarService,
    ClubService,
    FinanceService,
    MarketService,
    SquadService,
    StadiumService,
)
from app.services.player_development import TrainingService

router = APIRouter(tags=["game"], dependencies=[Depends(get_current_user)])
User = Annotated[object, Depends(get_current_user)]


def repository(database=Depends(get_database)):
    return GameRepository(database)


Repo = Annotated[GameRepository, Depends(repository)]


@router.get("/game/status")
def status(user: User, repo: Repo):
    return ClubService(repo).status(user)


@router.get("/game/catalog")
def catalog(repo: Repo):
    return ClubService(repo).catalog()


@router.post("/clubs", status_code=201)
def create_club(data: ClubInput, user: User, repo: Repo):
    return ClubService(repo).create(user, data)


@router.get("/clubs/{identity}")
def club(identity: str, repo: Repo):
    return ClubService(repo).club(identity)


@router.get("/squad")
def squad(user: User, repo: Repo):
    return SquadService(repo).get(user)


@router.put("/squad/lineup")
def lineup(data: LineupInput, user: User, repo: Repo):
    return SquadService(repo).save(user, data)


@router.get("/stadium")
def stadium(user: User, repo: Repo):
    return StadiumService(repo).get(user)


@router.post("/stadium/{facility}/upgrade")
def upgrade(facility: str, user: User, repo: Repo):
    return StadiumService(repo).upgrade(user, facility)


@router.get("/finance")
def finance(user: User, repo: Repo):
    return FinanceService(repo).summary(user)


@router.get("/finance/bank")
def bank(user: User, repo: Repo):
    return FinanceService(repo).bank(user)


@router.post("/finance/bank/{kind}", status_code=201)
def bank_contract(
    kind: Literal["investment", "bank_loan"], data: MoneyInput, user: User, repo: Repo
):
    return FinanceService(repo).contract(user, kind, data.amount)


@router.post("/finance/contracts/{identity}/settle")
def settle(identity: str, user: User, repo: Repo):
    return FinanceService(repo).settle(user, identity)


@router.get("/finance/tickets")
def tickets(user: User, repo: Repo):
    return FinanceService(repo).tickets(user)


@router.put("/finance/tickets")
def ticket_price(data: TicketInput, user: User, repo: Repo):
    return FinanceService(repo).ticket_price(user, data.price)


@router.get("/finance/sponsors")
def sponsors(user: User, repo: Repo):
    return FinanceService(repo).sponsors(user)


@router.post("/finance/sponsors/{identity}/accept")
def sponsor(identity: str, user: User, repo: Repo):
    return FinanceService(repo).sponsor(user, identity)


@router.get("/calendar")
def calendar(user: User, repo: Repo, filters: Annotated[CalendarFilter, Query()]):
    return CalendarService(repo).get(user, filters)


@router.get("/market/players")
def search(
    repo: Repo,
    name: str | None = Query(None, max_length=60),
    position: Literal["GOL", "GK", "DEF", "MED", "MID", "ATA", "ATT"] | None = None,
    country_id: str | None = None,
    type: Literal["sale", "loan"] | None = None,
    age_min: int | None = Query(None, ge=0),
    age_max: int | None = Query(None, ge=0),
    overall_min: int | None = Query(None, ge=0, le=100),
    overall_max: int | None = Query(None, ge=0, le=100),
    value_min: int | None = Query(None, ge=0),
    value_max: int | None = Query(None, ge=0),
):
    return MarketService(repo).search(
        {key: value for key, value in locals().items() if key != "repo"}
    )


@router.get("/market/mine")
def mine(user: User, repo: Repo):
    return MarketService(repo).mine(user)


@router.get("/players/{identity}")
def player(identity: str, repo: Repo):
    return MarketService(repo).player(identity)


@router.post("/market/listings", status_code=201)
def listing(data: ListingInput, user: User, repo: Repo):
    return MarketService(repo).list_player(user, data)


@router.post("/market/listings/{identity}/cancel")
def cancel_listing(identity: str, user: User, repo: Repo):
    return MarketService(repo).close(user, "transfer_listings", identity)


@router.post("/market/offers", status_code=201)
def offer(data: OfferInput, user: User, repo: Repo):
    return MarketService(repo).offer(user, data)


@router.post("/market/offers/{identity}/accept")
def accept(identity: str, user: User, repo: Repo):
    return MarketService(repo).accept(user, identity)


@router.post("/market/offers/{identity}/cancel")
def cancel_offer(identity: str, user: User, repo: Repo):
    return MarketService(repo).close(user, "transfer_offers", identity)


@router.get("/competition")
def competition(user: User, repo: Repo):
    return CompetitionService(repo).table(user)


@router.get("/competition/matches")
def competition_matches(user: User, repo: Repo):
    return CompetitionService(repo).matches(user)


@router.get("/training")
def training(user: User, repo: Repo):
    return TrainingService(repo).get(user)


@router.post("/players/{identity}/train")
def train(identity: str, user: User, repo: Repo):
    return TrainingService(repo).train(user, identity)


@router.get("/youth")
def youth(user: User, repo: Repo):
    return TrainingService(repo).get(user, youth=True)


@router.post("/youth/{identity}/promote")
def promote(identity: str, user: User, repo: Repo):
    return TrainingService(repo).promote(user, identity)
