from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.database.mongo import get_database
from app.models.game import public
from app.repositories.game import GameRepository
from app.schemas.game import (
    CalendarFilter,
    ClubInput,
    CounterOfferInput,
    FriendlyInput,
    LineupInput,
    ListingInput,
    MatchCommandInput,
    MoneyInput,
    NegotiationInput,
    OfferInput,
    PlayerContractInput,
    TacticsInput,
    TicketInput,
    TrainingInput,
    TransferStatusInput,
)
from app.services.competition import CompetitionService
from app.services.cup import CupService
from app.services.game import (
    CalendarService,
    ClubService,
    FinanceService,
    MarketService,
    SquadService,
    StadiumService,
)
from app.services.player_contracts import ContractService
from app.services.player_development import TrainingService
from app.services.player_statistics import PlayerStatisticsService
from app.services.tactics import TacticsService

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
    position: Literal["GOL", "GK", "DEF", "FB", "CB", "MED", "MID", "ATA", "ATT"] | None = None,
    country_id: str | None = None,
    status: Literal["free_agent"] | None = None,
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
def train(identity: str, user: User, repo: Repo, data: TrainingInput | None = None):
    return TrainingService(repo).train(user, identity, data.skill if data else None)


@router.get("/youth")
def youth(user: User, repo: Repo):
    return TrainingService(repo).get(user, youth=True)


@router.post("/youth/{identity}/promote")
def promote(identity: str, user: User, repo: Repo):
    return TrainingService(repo).promote(user, identity)


@router.get("/tactics")
def tactics(user: User, repo: Repo):
    return TacticsService(repo).get(user)


@router.put("/tactics")
def save_tactics(data: TacticsInput, user: User, repo: Repo):
    return TacticsService(repo).save(user, data)


@router.post("/competition/matches/{identity}/commands")
def match_command(identity: str, data: MatchCommandInput, user: User, repo: Repo):
    return TacticsService(repo).command(user, identity, data)


@router.get("/players/{identity}/contract")
def player_contract(identity: str, user: User, repo: Repo):
    return ContractService(repo).get(user, identity)


@router.post("/players/{identity}/contract/renew")
def renew_contract(identity: str, data: PlayerContractInput, user: User, repo: Repo):
    return ContractService(repo).renew(user, identity, data)


@router.post("/market/players/{identity}/sign", status_code=201)
def sign_free_agent(identity: str, data: PlayerContractInput, user: User, repo: Repo):
    return ContractService(repo).sign(user, identity, data)


@router.get("/statistics")
def statistics(
    user: User,
    repo: Repo,
    ranking: Literal["goals", "matches", "cards"] = "goals",
    season_id: str | None = None,
):
    club = repo.owned(user.id)
    return PlayerStatisticsService(repo).rankings(ranking, season_id, club["_id"])


@router.get("/players/{identity}/statistics")
def player_statistics(identity: str, repo: Repo):
    return PlayerStatisticsService(repo).player(identity)


@router.get("/competition/matches/{identity}")
def match_report(identity: str, user: User, repo: Repo):
    return PlayerStatisticsService(repo).report(user, identity)


@router.get("/competition/cup")
def cup(user: User, repo: Repo):
    return CupService(repo).summary(user)


@router.get("/clubs/ranking/current")
def club_ranking(repo: Repo):
    from app.models.game import public

    return public(
        repo.many(
            "clubs",
            {"active": {"$ne": False}, "ranking_position": {"$gt": 0}},
            sort=[("ranking_position", 1)],
            projection={"name": 1, "ranking_points": 1, "ranking_position": 1, "reputation": 1},
        )
    )


@router.post("/market/negotiations", status_code=201)
def negotiate(data: NegotiationInput, user: User, repo: Repo):
    from app.services.negotiation import NegotiationService

    return NegotiationService(repo).send(user, data)


@router.post("/market/negotiations/{identity}/counter")
def counter(identity: str, data: CounterOfferInput, user: User, repo: Repo):
    from app.services.negotiation import NegotiationService

    return NegotiationService(repo).act(user, identity, "counter", data)


@router.post("/market/negotiations/{identity}/{action}")
def negotiation_action(
    identity: str,
    action: Literal["accept", "reject", "confirm", "accept_counter"],
    user: User,
    repo: Repo,
):
    from app.services.negotiation import NegotiationService

    return NegotiationService(repo).act(user, identity, action)


@router.put("/players/{identity}/transfer-status")
def transfer_status(identity: str, data: TransferStatusInput, user: User, repo: Repo):
    from app.models.player import player_public
    from app.services.market_value import MarketValueService

    def operation(tx):
        club = tx.owned(user.id)
        player = tx.document("players", identity)
        if player["owner_club_id"] != club["_id"]:
            raise HTTPException(403, "Jogador de outro clube.")
        if tx.find("transfer_listings", {"player_id": player["_id"], "status": "active"}):
            raise HTTPException(409, "Retire o anúncio antes de alterar a disponibilidade.")
        return player_public(
            tx.update(
                "players",
                {"_id": player["_id"]},
                {
                    "$set": {
                        "player_transfer_status": data.status,
                        "asking_price": MarketValueService.asking_price(player, data.status),
                    }
                },
            )
        )

    return repo.transaction(operation)


@router.post("/youth/{identity}/release")
def release_youth(identity: str, user: User, repo: Repo):
    return TrainingService(repo).release(user, identity)


@router.post("/calendar/friendlies", status_code=201)
def friendly(data: FriendlyInput, user: User, repo: Repo):
    from app.services.season_calendar import FriendlyService

    return FriendlyService(repo).create(user, data)


@router.post("/calendar/friendlies/{identity}/accept")
def friendly_accept(identity: str, user: User, repo: Repo):
    from app.services.season_calendar import FriendlyService

    return FriendlyService(repo).accept(user, identity)


@router.get("/calendar/friendlies")
def friendly_list(user: User, repo: Repo):
    club = repo.owned(user.id)
    return public(
        repo.many(
            "friendly_matches",
            {"$or": [{"home_club_id": club["_id"]}, {"away_club_id": club["_id"]}]},
            limit=None,
            sort=[("date", 1)],
        )
    )


@router.post("/finance/loans/{product}", status_code=201)
def loan_contract(
    product: Literal["short_term", "medium_term", "long_term"],
    data: MoneyInput,
    user: User,
    repo: Repo,
):
    from app.services.bank_loans import BankLoanService

    return repo.transaction(
        lambda tx: BankLoanService.contract(tx, tx.owned(user.id)["_id"], product, data.amount)
    )


@router.post("/finance/loans/{identity}/settle")
def loan_settle(identity: str, user: User, repo: Repo):
    from app.services.bank_loans import BankLoanService

    return repo.transaction(
        lambda tx: BankLoanService.settle(tx, tx.owned(user.id)["_id"], identity)
    )


@router.get("/news")
def news(user: User, repo: Repo, scope: Literal["club", "universe"] = "club"):
    from app.services.news import NewsService

    return NewsService.feed(repo, repo.owned(user.id)["_id"] if scope == "club" else None)


@router.get("/history")
def history(user: User, repo: Repo):
    from app.services.game_history import HistoryService

    return HistoryService.get(repo, repo.owned(user.id)["_id"])
