import logging
from collections import Counter
from datetime import timedelta
from time import perf_counter

from bson import ObjectId
from fastapi import HTTPException
from pymongo import timeout
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.config.game import GameConfig, legacy_position
from app.config.stadium import (
    DEFAULT_FACILITIES,
    FACILITY_DEFINITIONS,
    FACILITY_LEVEL_NAMES,
    SECTOR_NAMES,
    STADIUM_LEVELS,
    arena_level,
    effects,
    facilities,
    sectors,
)
from app.config.team_performance import MoraleConfig
from app.models.game import FACILITIES, public, utcnow
from app.models.player import choose_shirt_number, player_public
from app.services.bank_loans import PRODUCTS, BankLoanService
from app.services.chemistry import ChemistryService
from app.services.club_prestige import ClubRankingService
from app.services.competition import CompetitionService
from app.services.fan_base import FanBaseService
from app.services.market_value import MarketValueService
from app.services.monthly_finance import MonthlyFinanceService
from app.services.player_contracts import ContractService
from app.services.player_development import PlayerGeneratorService
from app.services.player_morale import PlayerMoraleService
from app.services.tactics import TacticsService

logger = logging.getLogger(__name__)


class ClubService:
    def __init__(self, repository):
        self.repo = repository

    def status(self, user):
        club = self.repo.find("clubs", {"owner_user_id": ObjectId(user.id)})
        return {"club": self.response(club) if club else None}

    def resign(self, user, identity):
        CompetitionService.ensure_lock(self.repo)

        def operation(repo):
            from app.services.live_match import busy_clubs

            CompetitionService.lock(repo)
            club = repo.owned(user.id)
            if str(club["_id"]) != identity:
                raise HTTPException(403, "Você só pode pedir demissão do seu próprio clube.")
            if club["_id"] in busy_clubs(repo):
                raise HTTPException(409, "Aguarde o fim da partida para pedir demissão.")
            now = utcnow()
            repo.update(
                "clubs",
                {"_id": club["_id"]},
                {
                    "$set": {
                        "active": True,
                        "is_bot": True,
                        "bot_takeover": True,
                        "owner_user_id": None,
                        "previous_owner_user_id": ObjectId(user.id),
                        "resigned_at": now,
                    },
                    "$inc": {"roster_revision": 1},
                },
            )
            season = CompetitionService.current(repo)
            for collection in ("season_clubs", "standings"):
                repo.update_many(
                    collection,
                    {"club_id": club["_id"], "season_id": season["_id"] if season else None},
                    {"$set": {"is_bot": True, "bot_takeover": True}},
                )
            # The same club and its assets continue under bot management.
            return {"club": None}

        return self.repo.transaction(operation)

    def catalog(self):
        return public(
            {
                "countries": self.repo.many("countries", {}, limit=None, sort=[("name", 1)]),
                "badges": self.repo.many("club_badges", {}, limit=None),
            }
        )

    def club(self, identity):
        club = self.repo.document("clubs", identity)
        return self.response(club)

    @staticmethod
    def response(club):
        return public(
            {
                key: club.get(key)
                for key in [
                    "_id",
                    "name",
                    "country_id",
                    "badge_id",
                    "badge",
                    "country",
                    "created_at",
                    "ranking",
                    "competition_positions",
                    "trophies",
                    "supporters",
                    "fan_satisfaction",
                    "ranking_points",
                    "ranking_position",
                    "reputation",
                ]
            }
            | {"fan_confidence": FanBaseService.confidence(club)}
        )

    def create(self, user, data):
        started = perf_counter()
        logger.info("club_creation event=start user=%s", user.id)

        def operation(repo):
            logger.info("club_creation event=transaction_start user=%s", user.id)
            initialization = repo.find("game_state", {"_id": "initial_universe"})
            if initialization and initialization.get("status") == "preparing":
                raise HTTPException(
                    503, "A liga está sendo preparada. Aguarde a conclusão para criar o clube."
                )
            if repo.find("clubs", {"owner_user_id": ObjectId(user.id)}):
                raise HTTPException(409, "Você já possui um clube.")
            country = repo.find("countries", {"_id": data.country_id})
            badge = repo.find("club_badges", {"_id": data.badge_id})
            if not country or not badge:
                raise HTTPException(422, "País ou escudo inválido.")
            rules, now, club_id = repo.rules(), utcnow(), ObjectId()
            club = repo.insert(
                "clubs",
                {
                    "_id": club_id,
                    "owner_user_id": ObjectId(user.id),
                    **data.model_dump(exclude={"stadium_name"}),
                    "country": public(country),
                    "badge": public(badge),
                    "created_at": now,
                    "ranking": 0,
                    "competition_positions": [],
                    "trophies": [],
                },
            )
            # Claim the sporting slot before the expensive roster and finance work.
            # A conflict retries here, without discarding a fully built squad.
            competition = CompetitionService(repo)
            competition.enroll(repo, club, now, lock_universe=False)
            logger.info("club_creation event=slot_reserved club=%s", club_id)
            players = PlayerGeneratorService(GameConfig.from_rules(rules), str(club_id)).squad(
                club_id, data.country_id
            )
            repo.insert_many("players", players)
            starters = []
            for position, count in {"GOL": 1, **rules["formations"]["4-4-2"]}.items():
                starters.extend(
                    p["_id"]
                    for p in [p for p in players if legacy_position(p["position"]) == position][
                        :count
                    ]
                )
            repo.insert(
                "lineups",
                {
                    "_id": club_id,
                    "formation": "4-4-2",
                    "starters": starters,
                    "reserves": [p["_id"] for p in players if p["_id"] not in starters],
                },
            )

            TacticsService.persist(
                repo,
                club_id,
                {
                    "formation": "4-4-2",
                    "play_style": "balanced",
                    "marking": "light",
                    "attack_focus": "normal",
                },
            )
            repo.insert(
                "stadiums",
                {
                    "_id": club_id,
                    "name": data.stadium_name
                    or (repo.find("users", {"_id": ObjectId(user.id)}) or {}).get("stadium_name")
                    or f"Estádio {data.name}",
                    "capacity": rules["initial_capacity"],
                    "ticket_price": rules["ticket_price"],
                    "facilities": dict(DEFAULT_FACILITIES),
                },
            )
            repo.insert("club_finances", {"_id": club_id, "balance": 0})
            MonthlyFinanceService.initialize(repo, club_id, now)
            FanBaseService.initialize(repo, club_id)
            ChemistryService().save(repo, club_id, {})
            ContractService.initial(repo, players, GameConfig.from_rules(rules), now)
            logger.info("club_creation event=roster_and_finances_ready club=%s", club_id)
            season = competition.current(repo)
            competition.generate_youth(repo, club, season, competition.season_config(season))
            ClubRankingService.refresh(repo, season["_id"])
            logger.info("club_creation event=ranking_ready club=%s", club_id)
            MarketValueService().recalculate(repo, players, "initial", now=now)
            logger.info("club_creation event=ready_to_commit club=%s", club_id)
            return self.response(repo.find("clubs", {"_id": club_id}))

        try:
            # Bound lock contention and transaction retries within the request budget.
            with timeout(45):
                result = self.repo.transaction(operation)
            logger.info(
                "club_creation event=committed club=%s elapsed_ms=%d",
                result["id"],
                (perf_counter() - started) * 1000,
            )
            return result
        except DuplicateKeyError as exc:
            logger.exception("club_creation event=duplicate_key user=%s", user.id)
            if "owner_user_id" in (exc.details or {}).get("keyPattern", {}) or (
                "owner_user_id" in str(exc)
            ):
                raise HTTPException(409, "Você já possui um clube.") from exc
            raise
        except PyMongoError as exc:
            logger.exception(
                "club_creation event=failed user=%s code=%s elapsed_ms=%d",
                user.id,
                getattr(exc, "code", None),
                (perf_counter() - started) * 1000,
            )
            if exc.timeout:
                raise HTTPException(
                    503,
                    "A criação do clube demorou além do esperado. Tente novamente em instantes.",
                ) from exc
            raise


class SquadService:
    def __init__(self, repository):
        self.repo = repository

    def get(self, user):
        club = self.repo.owned(user.id)
        players = self.repo.many(
            "players", {"current_club_id": club["_id"], "status": {"$ne": "retired"}}, limit=None
        )
        if self.needs_shirt_numbers(players):
            players = self.repo.transaction(lambda repo: self.ensure_shirt_numbers(repo, user))
        lineup = self.repo.find("lineups", {"_id": club["_id"]})
        lineup = {**lineup, "reserves": lineup.get("reserves", [])[:5]}
        identities = [player["_id"] for player in players]
        contracts = {
            row["player_id"]: row
            for row in self.repo.many(
                "player_contracts",
                {"player_id": {"$in": identities}, "status": {"$in": ["active", "expiring"]}},
                projection={"player_id": 1, "salary": 1, "expires_at": 1, "status": 1},
                limit=None,
            )
        }
        statistics = {
            row["_id"]: row
            for row in self.repo.many(
                "player_career_stats",
                {"_id": {"$in": identities}},
                projection={
                    "matches": 1,
                    "goals": 1,
                    "minutes": 1,
                    "yellow_cards": 1,
                    "red_cards": 1,
                },
                limit=None,
            )
        }
        return public(
            {
                "players": [
                    {
                        **player_public(player),
                        "contract": contracts.get(player["_id"]),
                        "statistics": statistics.get(player["_id"]),
                    }
                    for player in players
                ],
                "team_chemistry": ChemistryService().get(self.repo, club["_id"])["value"],
                "lineup": lineup,
                "formations": self.repo.rules()["formations"],
            }
        )

    @staticmethod
    def needs_shirt_numbers(players):
        counts = Counter(p.get("shirt_number") for p in players)
        return any(
            not p.get("shirt_number_custom")
            and (
                p.get("shirt_number_revision") != 2
                or p.get("shirt_number") is None
                or counts[p.get("shirt_number")] > 1
            )
            for p in players
        )

    @classmethod
    def ensure_shirt_numbers(cls, repo, user):
        return cls.ensure_shirt_numbers_for_club(repo, repo.owned(user.id))

    @staticmethod
    def ensure_shirt_numbers_for_club(repo, club):
        # Number assignment and manual edits share this write lock.
        repo.update("clubs", {"_id": club["_id"]}, {"$inc": {"roster_revision": 1}})
        players = repo.many(
            "players",
            {"current_club_id": club["_id"], "status": {"$ne": "retired"}},
            limit=None,
            sort=[("_id", 1)],
        )
        counts = Counter(p.get("shirt_number") for p in players)
        preserved = [
            p
            for p in players
            if p.get("shirt_number") is not None
            and (
                p.get("shirt_number_custom")
                or p.get("shirt_number_revision") == 2
                and counts[p["shirt_number"]] == 1
            )
        ]
        used = {p["shirt_number"] for p in preserved}
        for player in players:
            if player in preserved:
                continue
            try:
                number = choose_shirt_number(player.get("position"), used)
            except ValueError as error:
                raise HTTPException(409, str(error)) from error
            values = {
                "shirt_number": number,
                "shirt_number_revision": 2,
                "shirt_number_custom": False,
            }
            repo.update("players", {"_id": player["_id"]}, {"$set": values})
            player.update(values)
            used.add(number)
        return players

    def shirt_number(self, user, identity, number):
        def operation(repo):
            club = repo.owned(user.id)
            repo.update("clubs", {"_id": club["_id"]}, {"$inc": {"roster_revision": 1}})
            player = repo.document("players", identity)
            if player.get("current_club_id") != club["_id"] or player.get("status") == "retired":
                raise HTTPException(403, "O jogador não pertence ao seu plantel.")
            if repo.find(
                "players",
                {
                    "current_club_id": club["_id"],
                    "status": {"$ne": "retired"},
                    "shirt_number": number,
                    "_id": {"$ne": player["_id"]},
                },
            ):
                raise HTTPException(409, "Este número de camisa já está em uso no plantel.")
            updated = repo.update(
                "players",
                {"_id": player["_id"]},
                {
                    "$set": {
                        "shirt_number": number,
                        "shirt_number_revision": 2,
                        "shirt_number_custom": True,
                    }
                },
            )
            return player_public(updated)

        return self.repo.transaction(operation)

    def save(self, user, data):
        def operation(repo):
            club = repo.owned(user.id)
            formation = repo.rules()["formations"].get(data.formation)
            ids = data.starters + data.reserves
            if (
                formation is None
                or len(set(ids)) != len(ids)
                or any(not ObjectId.is_valid(p) for p in ids)
            ):
                raise HTTPException(422, "Formação ou jogadores inválidos/duplicados.")
            players = repo.many(
                "players",
                {"current_club_id": club["_id"], "status": {"$ne": "retired"}},
                limit=None,
            )
            if not set(ids).issubset(
                {str(p["_id"]) for p in players if p.get("status") not in {"injured", "suspended"}}
            ):
                raise HTTPException(
                    422, "Escalação deve incluir apenas jogadores disponíveis do plantel."
                )
            selected = set(data.starters + data.reserves)
            if any(
                p.get("status") in {"injured", "suspended"} and str(p["_id"]) in selected
                for p in players
            ):
                raise HTTPException(
                    422, "Lesionados e suspensos não podem ser titulares ou reservas."
                )
            positions = Counter(
                legacy_position(p["position"]) for p in players if str(p["_id"]) in data.starters
            )
            manual_keeper = next((p for p in players if str(p["_id"]) == data.starters[0]), None)
            if (
                len(data.starters) != 11
                or positions["GOL"] != 1
                or (data.manual_positions and legacy_position(manual_keeper["position"]) != "GOL")
            ):
                raise HTTPException(422, "São necessários 11 titulares e exatamente um goleiro.")

            previous = repo.find("lineups", {"_id": club["_id"]})
            ChemistryService().lineup_change(
                repo, club["_id"], previous, [ObjectId(p) for p in data.starters], data.formation
            )
            settings = TacticsService.settings(repo, club["_id"], {"formation": data.formation})
            TacticsService.persist(
                repo,
                club["_id"],
                {
                    **{k: settings[k] for k in ("play_style", "marking", "attack_focus")},
                    "formation": data.formation,
                },
            )
            # Also locks the roster against concurrent transfers.
            repo.update("clubs", {"_id": club["_id"]}, {"$inc": {"roster_revision": 1}})
            return public(
                repo.update(
                    "lineups",
                    {"_id": club["_id"]},
                    {
                        "$set": {
                            "formation": data.formation,
                            "manual_positions": data.manual_positions,
                            "starters": [ObjectId(p) for p in data.starters],
                            "reserves": [ObjectId(p) for p in data.reserves],
                        }
                    },
                )
            )

        return self.repo.transaction(operation)


class StadiumService:
    def __init__(self, repository):
        self.repo = repository

    def get(self, user):
        club = self.repo.owned(user.id)
        stadium = self.repo.find("stadiums", {"_id": club["_id"]})
        f = facilities(stadium)
        level = arena_level(stadium)
        base_cost = self.repo.rules()["upgrade_base_cost"]
        costs = {
            key: max(1, current) * definition[2] * base_cost
            for key, definition in FACILITY_DEFINITIONS.items()
            for current in (f[key],)
        }
        return public(
            {
                **stadium,
                "facilities": f,
                "names": FACILITIES,
                "upgrade_costs": costs,
                "arena_level": level,
                "arena_name": STADIUM_LEVELS[level - 1][1],
                "levels": [
                    {
                        "level": n,
                        "name": name,
                        "capacity": capacity,
                        "cost": cost,
                        "description": description,
                    }
                    for n, name, capacity, cost, description in STADIUM_LEVELS
                ],
                "facility_level_names": FACILITY_LEVEL_NAMES,
                "facility_catalog": {
                    key: {
                        "name": definition[0],
                        "minimum_arena_level": definition[1],
                        "maximum_level": max(5, f[key]),
                        "icon": definition[3],
                        "benefit": definition[4],
                        "level_name": FACILITY_LEVEL_NAMES[min(5, max(0, f[key]))],
                    }
                    for key, definition in FACILITY_DEFINITIONS.items()
                },
                "effects": effects(stadium),
                "sectors": sectors(stadium),
            }
        )

    def upgrade(self, user, facility):
        self.repo.transaction(
            lambda repo: self.upgrade_for_club(repo, repo.owned(user.id), facility)
        )
        return self.get(user)

    @staticmethod
    def upgrade_for_club(repo, club, facility):
        if facility not in FACILITY_DEFINITIONS:
            raise HTTPException(404, "Construção não encontrada.")
        stadium = repo.update(
            "stadiums", {"_id": club["_id"]}, {"$inc": {"construction_revision": 1}}
        )
        definition = FACILITY_DEFINITIONS[facility]
        level = facilities(stadium)[facility]
        if arena_level(stadium) < definition[1]:
            raise HTTPException(409, f"Esta melhoria exige estádio de nível {definition[1]}.")
        if level >= 5:
            raise HTTPException(409, "Esta instalação já atingiu o nível máximo.")
        cost = max(1, level) * definition[2] * repo.rules()["upgrade_base_cost"]
        repo.money(club["_id"], -cost, "stadium")
        update = {"$set": {f"facilities.{facility}": level + 1}}
        if facility in {"stands", "upper_stands"}:
            update["$inc"] = {"capacity": 1000}
        repo.update("stadiums", {"_id": club["_id"]}, update)
        repo.event(club["_id"], "stadium", FACILITIES[facility])

    def evolve(self, user):
        def operation(repo):
            club = repo.owned(user.id)
            stadium = repo.update(
                "stadiums", {"_id": club["_id"]}, {"$inc": {"construction_revision": 1}}
            )
            current = arena_level(stadium)
            if current == len(STADIUM_LEVELS):
                raise HTTPException(409, "O estádio já atingiu o nível máximo.")
            level, name, capacity, cost, _ = STADIUM_LEVELS[current]
            repo.money(club["_id"], -cost, "stadium")
            changes = {"capacity": capacity}
            if level >= 3:
                changes["facilities.upper_stands"] = max(1, facilities(stadium)["upper_stands"])
            repo.update("stadiums", {"_id": club["_id"]}, {"$set": changes})
            repo.event(club["_id"], "stadium", f"Evolução para {name}")

        self.repo.transaction(operation)
        return self.get(user)

    def price_sector(self, user, sector, price):
        if sector not in SECTOR_NAMES:
            raise HTTPException(404, "Setor não encontrado.")

        def operation(repo):
            club = repo.owned(user.id)
            stadium = repo.update(
                "stadiums", {"_id": club["_id"]}, {"$inc": {"pricing_revision": 1}}
            )
            if not next(s for s in sectors(stadium) if s["id"] == sector)["available"]:
                raise HTTPException(409, "Este setor ainda não foi construído.")
            repo.update(
                "stadiums", {"_id": club["_id"]}, {"$set": {f"sector_prices.{sector}": price}}
            )

        self.repo.transaction(operation)
        return self.get(user)


class FinanceService:
    def __init__(self, repository):
        self.repo = repository

    def summary(self, user):
        club = self.repo.owned(user.id)
        return public(
            {
                **self.repo.find("club_finances", {"_id": club["_id"]}),
                **ContractService(self.repo).finance(club["_id"]),
                **MonthlyFinanceService.summary(self.repo, club["_id"]),
                "transactions": self.repo.many(
                    "financial_transactions", {"club_id": club["_id"]}, sort=[("created_at", -1)]
                ),
            }
        )

    def bank(self, user):
        club = self.repo.owned(user.id)
        return public(
            {
                "contracts": self.repo.many("bank_contracts", {"club_id": club["_id"]}),
                "loans": self.repo.many("club_loans", {"club_id": club["_id"]}),
                "products": PRODUCTS,
                **BankLoanService.credit(self.repo, club["_id"]),
                "rules": {
                    key: value
                    for key, value in self.repo.rules().items()
                    if key.startswith(("investment", "bank_loan", "max_bank"))
                },
            }
        )

    def contract(self, user, kind, amount):
        def operation(repo):
            club, rules, now = repo.owned(user.id), repo.rules(), utcnow()
            repo.update("club_finances", {"_id": club["_id"]}, {"$inc": {"credit_revision": 1}})
            credit = BankLoanService.credit(repo, club["_id"])
            if kind == "investment" and credit["debt"]:
                raise HTTPException(409, "Quite os empréstimos antes de investir.")
            if kind == "bank_loan" and (
                amount > credit["credit_limit"]
                or repo.find(
                    "bank_contracts",
                    {"club_id": club["_id"], "type": "investment", "status": "active"},
                )
            ):
                raise HTTPException(
                    409, "Crédito indisponível enquanto houver investimentos ou dívida em atraso."
                )
            if kind == "bank_loan":
                if amount > rules["max_bank_loan"] or repo.find(
                    "bank_contracts", {"club_id": club["_id"], "type": kind, "status": "active"}
                ):
                    raise HTTPException(409, "Limite de empréstimo excedido ou contrato ativo.")
            identity = ObjectId()
            contract = repo.insert(
                "bank_contracts",
                {
                    "_id": identity,
                    "club_id": club["_id"],
                    "type": kind,
                    "amount": amount,
                    "interest": amount * rules[f"{kind}_interest_bps"] // 10000,
                    "status": "active",
                    "starts_at": now,
                    "ends_at": now + timedelta(days=rules[f"{kind}_days"]),
                },
            )
            repo.money(club["_id"], amount if kind == "bank_loan" else -amount, kind, identity)
            repo.event(
                club["_id"], "financial", f"Vencimento: {kind}", contract["ends_at"], identity
            )
            return public(contract)

        return self.repo.transaction(operation)

    def settle(self, user, identity):
        def operation(repo):
            club, contract = repo.owned(user.id), repo.document("bank_contracts", identity)
            if contract["club_id"] != club["_id"]:
                raise HTTPException(403, "Contrato de outro clube.")
            if contract["status"] != "active":
                raise HTTPException(409, "Contrato já encerrado.")
            if contract["type"] == "investment" and contract["ends_at"] > utcnow():
                raise HTTPException(409, "Investimento ainda não venceu.")
            amount = contract["amount"] + contract["interest"]
            repo.money(
                club["_id"],
                amount if contract["type"] == "investment" else -amount,
                "bank_settlement",
                contract["_id"],
            )
            return public(
                repo.update(
                    "bank_contracts",
                    {"_id": contract["_id"], "status": "active"},
                    {"$set": {"status": "settled"}},
                )
            )

        return self.repo.transaction(operation)

    def tickets(self, user):
        club = self.repo.owned(user.id)
        stadium = self.repo.find("stadiums", {"_id": club["_id"]})
        sector_rows = FanBaseService.sector_ticketing(club, stadium)
        return public(
            {
                "price": stadium["ticket_price"],
                "capacity": stadium["capacity"],
                "history": self.repo.many("ticket_history", {"club_id": club["_id"]}),
                "income": self.repo.ticket_income(club["_id"]),
                "estimated_attendance": sum(row["attendance"] for row in sector_rows),
                "sectors": sector_rows,
                "attendance_share": FanBaseService.ATTENDANCE_SHARE,
                "supporters": club.get("supporters", 1000),
                "fan_satisfaction": club.get("fan_satisfaction", 50),
                "fan_confidence": FanBaseService.confidence(club),
                "reputation": club.get("reputation", 10),
            }
        )

    def ticket_price(self, user, price):
        def operation(repo):
            club = repo.owned(user.id)
            repo.update(
                "stadiums",
                {"_id": club["_id"]},
                {
                    "$set": {"ticket_price": price, "sector_prices": {}},
                    "$inc": {"pricing_revision": 1},
                },
            )

        self.repo.transaction(operation)
        return self.tickets(user)

    def sponsors(self, user):
        from app.services.sponsorship import SponsorshipService

        def operation(repo):
            club = repo.owned(user.id)
            return public(
                {
                    "contracts": repo.many("sponsor_contracts", {"club_id": club["_id"]}),
                    "offers": SponsorshipService.offers(repo, club),
                }
            )

        return self.repo.transaction(operation)

    def sponsor(self, user, identity):
        from app.services.sponsorship import SponsorshipService

        return self.repo.transaction(
            lambda repo: SponsorshipService.accept(repo, repo.owned(user.id), identity)
        )


class CalendarService:
    def __init__(self, repository):
        self.repo = repository

    def get(self, user, filters):
        club_id = self.repo.owned(user.id)["_id"]
        match_types = ("match", "league_match", "cup_match", "friendly")
        query = {
            "club_id": club_id,
            "$nor": [{"type": {"$in": match_types}}, {"kind": {"$in": match_types}}],
        }
        if filters.type:
            query["$or"] = [{"type": filters.type}, {"kind": filters.type}]
        dates = {}
        if filters.start:
            dates["$gte"] = filters.start
        if filters.end:
            dates["$lte"] = filters.end
        if filters.start and filters.end and filters.start > filters.end:
            raise HTTPException(422, "Período inválido.")
        if dates:
            query["date"] = dates
        events = self.repo.many("calendar_events", query, limit=500, sort=[("date", 1)])
        # Match documents are the same source used by Campeonatos. Copies in
        # calendar_events may be missing, duplicated or have an outdated date.
        matches, kinds = {}, {}
        slots = []
        if filters.type in (None, "match", "league_match"):
            slots = [
                slot["_id"]
                for slot in self.repo.many(
                    "season_clubs", {"club_id": club_id}, limit=None, projection={"_id": 1}
                )
            ]
        for collection, kind in (
            ("matches", "league_match"),
            ("competition_matches", "cup_match"),
            ("friendly_matches", "friendly"),
        ):
            if filters.type not in (None, "match", kind):
                continue
            participants = [{"home_club_id": club_id}, {"away_club_id": club_id}]
            if collection == "matches" and slots:
                participants += [{"home_slot_id": {"$in": slots}}, {"away_slot_id": {"$in": slots}}]
            fixture_query = {"$or": participants}
            if dates:
                fixture_query["date"] = dates
            for match in self.repo.many(
                collection,
                fixture_query,
                limit=500,
                sort=[("date", 1)],
                projection={
                    "date": 1,
                    "round": 1,
                    "phase": 1,
                    "division_id": 1,
                    "season_id": 1,
                    "status": 1,
                    "home_goals": 1,
                    "away_goals": 1,
                    "home_club_id": 1,
                    "away_club_id": 1,
                },
            ):
                matches[match["_id"]] = match
                kinds[match["_id"]] = kind
        division_ids = list({m["division_id"] for m in matches.values() if m.get("division_id")})
        divisions = (
            {
                d["_id"]: d["name"]
                for d in self.repo.many(
                    "divisions", {"_id": {"$in": division_ids}}, limit=None, projection={"name": 1}
                )
            }
            if division_ids
            else {}
        )
        club_ids = list(
            {
                match[key]
                for match in matches.values()
                for key in ("home_club_id", "away_club_id")
                if match.get(key)
            }
        )
        clubs = (
            {
                club["_id"]: club
                for club in self.repo.many(
                    "clubs", {"_id": {"$in": club_ids}}, limit=None, projection={"name": 1}
                )
            }
            if club_ids
            else {}
        )
        stadiums = (
            {
                stadium["_id"]: stadium
                for stadium in self.repo.many(
                    "stadiums", {"_id": {"$in": club_ids}}, limit=None, projection={"name": 1}
                )
            }
            if club_ids
            else {}
        )
        for match in matches.values():
            home, away = match.get("home_club_id"), match.get("away_club_id")
            if home in clubs:
                match["home_name"] = clubs[home]["name"]
                match["stadium_name"] = (
                    stadiums.get(home, {}).get("name") or f"Estádio {clubs[home]['name']}"
                )
            if away in clubs:
                match["away_name"] = clubs[away]["name"]
        for identity, match in matches.items():
            kind = kinds[identity]
            round_label = f"rodada {match.get('round', '?')}"
            if kind == "league_match":
                title = f"Série {divisions.get(match.get('division_id'), '?')} · {round_label}"
            elif kind == "cup_match":
                title = f"Copa Nacional · {match.get('phase') or round_label}"
            else:
                title = "Amistoso"
            events.append(
                {
                    **match,
                    "_id": f"{kind}:{identity}:{club_id}",
                    "club_id": club_id,
                    "type": "friendly" if kind == "friendly" else "match",
                    "kind": kind,
                    "title": title,
                    "reference_id": identity,
                }
            )
        return public(sorted(events, key=lambda event: (event["date"], str(event["_id"])))[:500])


class MarketService:
    def __init__(self, repository):
        self.repo = repository

    def player(self, identity):
        player = self.repo.document("players", identity)
        listing = self.repo.find(
            "transfer_listings", {"player_id": player["_id"], "status": "active"}
        )
        return player_public({**player, "listing": listing})

    def search(self, filters):
        query = {"status": {"$ne": "retired"}}
        for key in ["position", "country_id", "status"]:
            if filters.get(key):
                if key == "status" and filters[key] == "free_agent":
                    query["owner_club_id"] = None
                elif key == "position" and filters[key] in {"DEF", "GOL", "MED", "ATA"}:
                    query[key] = (
                        {"$in": ["DEF", "FB", "CB"]}
                        if filters[key] == "DEF"
                        else {"GOL": "GK", "MED": "MID", "ATA": "ATT"}[filters[key]]
                    )
                else:
                    query[key] = filters[key]
        if filters.get("name"):
            import re

            query["name"] = {"$regex": re.escape(filters["name"]), "$options": "i"}
        for key in ["age", "overall", "value"]:
            bounds = {}
            for suffix, operator in [("min", "$gte"), ("max", "$lte")]:
                value = filters.get(f"{key}_{suffix}")
                if value is not None:
                    bounds[operator] = value
            if bounds:
                query[key] = bounds
        return [
            player_public(p)
            for p in self.repo.search_players(
                query, filters.get("type"), filters.get("sort", "value_asc")
            )
        ]

    def mine(self, user):
        club = self.repo.owned(user.id)
        listings = self.repo.many(
            "transfer_listings", {"seller_club_id": club["_id"], "negotiation_only": {"$ne": True}}
        )
        return public(
            {
                "listings": listings,
                "incoming": self.repo.many("transfer_offers", {"seller_club_id": club["_id"]}),
                "outgoing": self.repo.many("transfer_offers", {"buyer_club_id": club["_id"]}),
                "loans": self.repo.many(
                    "player_loans",
                    {
                        "$or": [
                            {"owner_club_id": club["_id"]},
                            {"current_club_id": club["_id"]},
                        ]
                    },
                ),
            }
        )

    def list_player(self, user, data):
        try:
            return self.repo.transaction(
                lambda repo: self.list_for_club(repo, repo.owned(user.id), data)
            )
        except DuplicateKeyError as exc:
            raise HTTPException(409, "Jogador já anunciado.") from exc

    @staticmethod
    def list_for_club(repo, club, data):
        player = repo.document("players", data.player_id)
        if player["owner_club_id"] != club["_id"] or player["current_club_id"] != club["_id"]:
            raise HTTPException(
                403, "Só é possível anunciar jogadores próprios e presentes no clube."
            )
        if player.get("status") == "retired":
            raise HTTPException(409, "Jogador aposentado.")
        value = player.get("market_value", player.get("value", 50000))
        asking = (
            max(
                round(value * 0.9 / 10000) * 10000,
                min(round(value * 1.1 / 10000) * 10000, round(data.price / 10000) * 10000),
            )
            if data.type == "sale"
            else data.price
        )
        lineup = repo.find("lineups", {"_id": club["_id"]})
        if player["_id"] in lineup["starters"]:
            raise HTTPException(409, "Mova o jogador para a reserva antes de anunciá-lo.")
        repo.update(
            "players",
            {"_id": player["_id"]},
            {
                "$set": {
                    "player_transfer_status": "listed" if data.type == "sale" else "loan_listed",
                    "asking_price": asking,
                }
            },
        )
        PlayerMoraleService().change(repo, player, MoraleConfig().future_transfer)
        repo.update("clubs", {"_id": club["_id"]}, {"$inc": {"roster_revision": 1}})
        return public(
            repo.insert(
                "transfer_listings",
                {
                    "_id": ObjectId(),
                    "player_id": player["_id"],
                    "seller_club_id": club["_id"],
                    "type": data.type,
                    "price": asking,
                    "duration_days": data.duration_days,
                    "status": "active",
                    "created_at": utcnow(),
                },
            )
        )

    def offer(self, user, data):
        # Keep the earlier request shape, but use the same staged settlement.
        from math import ceil

        from app.schemas.game import NegotiationInput
        from app.services.negotiation import NegotiationService

        def operation(repo):
            club = repo.owned(user.id)
            listing = repo.document("transfer_listings", data.listing_id)
            if listing["status"] != "active":
                raise HTTPException(409, "Anúncio indisponível.")
            player = repo.document("players", str(listing["player_id"]))
            contract = ContractService.current(repo, player["_id"])
            if not contract:
                raise HTTPException(409, "Jogador sem contrato vigente.")
            months = max(
                1,
                min(
                    60,
                    ceil(
                        (contract["expires_at"] - utcnow()).total_seconds()
                        / contract["salary_period_seconds"]
                    ),
                ),
            )
            loan_months = max(
                1,
                min(
                    12,
                    ceil(
                        listing["duration_days"]
                        * 12
                        / GameConfig.from_rules(repo.rules()).SEASON_DURATION_DAYS
                    ),
                ),
            )
            offer = NegotiationService.send_for_club(
                repo,
                club,
                NegotiationInput(
                    player_id=str(player["_id"]),
                    offer_type=listing["type"],
                    transfer_value=data.amount,
                    salary_offer=contract["salary"],
                    contract_months=months,
                    loan_months=loan_months,
                    salary_share=0,
                ),
            )
            return public(
                repo.update(
                    "transfer_offers",
                    {"_id": ObjectId(offer["id"])},
                    {"$set": {"keep_existing_contract": True}},
                )
            )

        return self.repo.transaction(operation)

    @staticmethod
    def repair_lineup(repo, club_id):
        players = repo.many(
            "players",
            {"current_club_id": club_id, "status": {"$nin": ["retired", "injured", "suspended"]}},
            limit=None,
        )
        lineup = repo.find("lineups", {"_id": club_id})
        available = {p["_id"] for p in players}
        if len(lineup["starters"]) == 11 and set(lineup["starters"]) <= available:
            repo.update(
                "lineups",
                {"_id": club_id},
                {
                    "$set": {
                        "reserves": [
                            p["_id"] for p in players if p["_id"] not in lineup["starters"]
                        ]
                    }
                },
            )
            return
        rules = repo.rules()["formations"]
        for formation in [lineup["formation"], *rules]:
            starters = []
            for position, count in {"GOL": 1, **rules[formation]}.items():
                choices = [p["_id"] for p in players if legacy_position(p["position"]) == position][
                    :count
                ]
                if len(choices) != count:
                    break
                starters.extend(choices)
            if len(starters) == 11:
                repo.update(
                    "lineups",
                    {"_id": club_id},
                    {
                        "$set": {
                            "formation": formation,
                            "starters": starters,
                            "reserves": [p["_id"] for p in players if p["_id"] not in starters],
                        }
                    },
                )

                settings = TacticsService.settings(repo, club_id, lineup)
                TacticsService.persist(
                    repo,
                    club_id,
                    {
                        **{k: settings[k] for k in ("play_style", "marking", "attack_focus")},
                        "formation": formation,
                    },
                )
                return
        raise HTTPException(409, "Transferência deixaria o clube sem escalação válida.")

    def accept(self, user, identity):
        from app.services.negotiation import NegotiationService

        return NegotiationService(self.repo).act(user, identity, "accept")

    @staticmethod
    def complete_for_club(repo, club, identity, now=None, terms=None):
        CompetitionService.require_transfer_window(repo, now)
        offer = repo.document("transfer_offers", identity)
        listing = repo.document("transfer_listings", str(offer["listing_id"]))
        if offer["seller_club_id"] != club["_id"]:
            raise HTTPException(403, "Proposta de outro clube.")
        if (
            offer["status"] != ("player_accepted" if terms else "pending")
            or listing["status"] != "active"
        ):
            raise HTTPException(409, "Proposta ou anúncio encerrado.")
        from app.services.live_match import busy_clubs

        if {club["_id"], offer["buyer_club_id"]} & busy_clubs(repo):
            raise HTTPException(409, "Aguarde o fim da partida para concluir a transferência.")
        player = repo.document("players", str(listing["player_id"]))
        if player["owner_club_id"] != club["_id"] or player["current_club_id"] != club["_id"]:
            raise HTTPException(409, "Jogador indisponível.")
        if player.get("status") == "retired":
            raise HTTPException(409, "Jogador aposentado.")
        contract = ContractService.current(repo, player["_id"])
        if not contract or contract["expires_at"] <= (now or utcnow()):
            raise HTTPException(409, "Jogador sem contrato vigente.")
        # Lock both rosters; simultaneous lineup/transfer changes are retried by MongoDB.
        for club_id in sorted([club["_id"], offer["buyer_club_id"]]):
            repo.update("clubs", {"_id": club_id}, {"$inc": {"roster_revision": 1}})
        repo.money(
            offer["buyer_club_id"],
            -offer["amount"],
            "player_purchase" if listing["type"] == "sale" else "other_expense",
            offer["_id"],
        )
        repo.money(
            club["_id"],
            offer["amount"],
            "player_sale" if listing["type"] == "sale" else "other_income",
            offer["_id"],
        )
        ownership = {
            "current_club_id": offer["buyer_club_id"],
            "joined_at": (now or utcnow()),
        }
        ChemistryService().recruit(repo, offer["buyer_club_id"])
        PlayerMoraleService().change(repo, player, MoraleConfig().transfer)
        if listing["type"] == "sale":
            ContractService.transfer(
                repo,
                player["_id"],
                offer["buyer_club_id"],
                salary=terms.get("salary_offer") if terms else None,
                months=terms.get("contract_months")
                if terms and not terms.get("keep_existing_contract")
                else None,
                now=now,
            )
            ownership["owner_club_id"] = offer["buyer_club_id"]
        else:
            if (
                terms
                and (now or utcnow())
                + timedelta(seconds=contract["salary_period_seconds"] * terms["loan_months"])
                > contract["expires_at"]
            ):
                raise HTTPException(409, "Empréstimo ultrapassa o contrato vigente.")
            ContractService.settle_salary(repo, contract, now or utcnow())
            ContractService.capacity(
                repo,
                offer["buyer_club_id"],
                round(contract["salary"] * (terms.get("salary_share", 0) if terms else 0)),
            )
            loan = repo.insert(
                "player_loans",
                {
                    "_id": ObjectId(),
                    "player_id": player["_id"],
                    "owner_club_id": club["_id"],
                    "current_club_id": offer["buyer_club_id"],
                    "starts_at": (now or utcnow()),
                    "salary_share": terms.get("salary_share", 0) if terms else 0,
                    "ends_at": (now or utcnow())
                    + timedelta(
                        days=(
                            terms["loan_months"]
                            * GameConfig.from_rules(repo.rules()).SEASON_DURATION_DAYS
                            / 12
                        )
                        if terms
                        else listing["duration_days"]
                    ),
                    "status": "active",
                },
            )
            for club_id in [club["_id"], offer["buyer_club_id"]]:
                repo.event(
                    club_id,
                    "transfer",
                    "Retorno previsto de empréstimo",
                    loan["ends_at"],
                    loan["_id"],
                )
        from app.services.game_history import HistoryService

        HistoryService.transfer(repo, player, offer, listing["type"], now or utcnow())
        repo.update("players", {"_id": player["_id"]}, {"$set": ownership})
        # A club must retain its own complete roster when borrowed players return.
        permanent = repo.many(
            "players",
            {
                "owner_club_id": club["_id"],
                "current_club_id": club["_id"],
                "status": {"$ne": "retired"},
            },
            limit=None,
        )
        counts = Counter(legacy_position(p["position"]) for p in permanent)
        if not any(
            counts["GOL"] >= 1 and all(counts[p] >= n for p, n in f.items())
            for f in repo.rules()["formations"].values()
        ):
            raise HTTPException(
                409, "O clube deve manter jogadores próprios para uma escalação válida."
            )
        for club_id in [club["_id"], offer["buyer_club_id"]]:
            MarketService.repair_lineup(repo, club_id)
            repo.event(
                club_id,
                "transfer",
                f"Transferência de {player['name']}",
                reference=offer["_id"],
            )
        repo.insert(
            "transfer_history",
            {
                "_id": ObjectId(),
                "player_id": player["_id"],
                "seller_club_id": club["_id"],
                "buyer_club_id": offer["buyer_club_id"],
                "type": listing["type"],
                "amount": offer["amount"],
                "created_at": (now or utcnow()),
            },
        )
        repo.update("transfer_listings", {"_id": listing["_id"]}, {"$set": {"status": "closed"}})
        repo.update_many(
            "transfer_offers",
            {
                "listing_id": listing["_id"],
                "status": {"$in": ["pending", "counter_offer", "player_accepted"]},
            },
            {"$set": {"status": "closed"}},
        )
        MarketValueService().recalculate(
            repo, [repo.find("players", {"_id": player["_id"]})], "transfer", offer["_id"]
        )
        return public(
            repo.update("transfer_offers", {"_id": offer["_id"]}, {"$set": {"status": "accepted"}})
        )

    @staticmethod
    def return_loans(repo, now):
        for loan in repo.many("player_loans", {"status": "active", "ends_at": {"$lte": now}}):

            def return_player(repo, identity=loan["_id"]):
                current = repo.find("player_loans", {"_id": identity, "status": "active"})
                if not current:
                    return
                from app.services.live_match import busy_clubs

                if {current["owner_club_id"], current["current_club_id"]} & busy_clubs(repo):
                    return
                for club_id in sorted([current["owner_club_id"], current["current_club_id"]]):
                    repo.update("clubs", {"_id": club_id}, {"$inc": {"roster_revision": 1}})
                repo.update(
                    "players",
                    {"_id": current["player_id"]},
                    {
                        "$set": {
                            "current_club_id": current["owner_club_id"],
                            "joined_at": now,
                        }
                    },
                )
                ChemistryService().recruit(repo, current["owner_club_id"])
                for club_id in [current["owner_club_id"], current["current_club_id"]]:
                    try:
                        MarketService.repair_lineup(repo, club_id)
                    except HTTPException as exc:
                        if exc.status_code != 409:
                            raise
                    repo.event(club_id, "transfer", "Retorno de empréstimo", reference=identity)
                repo.update("player_loans", {"_id": identity}, {"$set": {"status": "returned"}})

            repo.transaction(return_player)

    def close(self, user, collection, identity):
        def operation(repo):
            club, document = repo.owned(user.id), repo.document(collection, identity)
            allowed = (
                [document["seller_club_id"]]
                if collection == "transfer_listings"
                else [document["seller_club_id"], document["buyer_club_id"]]
            )
            if club["_id"] not in allowed:
                raise HTTPException(403, "Negociação de outro clube.")
            status = "active" if collection == "transfer_listings" else "pending"
            if document["status"] not in (
                {"pending", "counter_offer", "player_accepted"}
                if document.get("negotiation_version") == 2
                else {status}
            ):
                raise HTTPException(409, "Negociação já encerrada.")
            repo.update(collection, {"_id": document["_id"]}, {"$set": {"status": "cancelled"}})
            if collection == "transfer_listings":
                repo.update_many(
                    "transfer_offers",
                    {
                        "listing_id": document["_id"],
                        "status": {"$in": ["pending", "counter_offer", "player_accepted"]},
                    },
                    {"$set": {"status": "closed"}},
                )
            return {"status": "cancelled"}

        return self.repo.transaction(operation)


def process_due(repository):
    now = utcnow()
    CompetitionService(repository).process_due(now)
    MonthlyFinanceService.process_due(repository, now)
    ContractService(repository).process_due(now)
    from app.services.bot_manager import BotManagerService

    BotManagerService(repository).process_due(now)
    from app.services.negotiation import NegotiationService

    NegotiationService.expire(repository, now)
    MarketService.return_loans(repository, now)
    for contract in repository.many(
        "bank_contracts", {"status": "active", "ends_at": {"$lte": now}}
    ):

        def settle(repo, identity=contract["_id"]):
            current = repo.find("bank_contracts", {"_id": identity, "status": "active"})
            if not current:
                return
            amount = current["amount"] + current["interest"]
            if (
                current["type"] == "bank_loan"
                and repo.find("club_finances", {"_id": current["club_id"]})["balance"] < amount
            ):
                repo.update("bank_contracts", {"_id": identity}, {"$set": {"overdue": True}})
                return
            repo.money(
                current["club_id"],
                amount if current["type"] == "investment" else -amount,
                "bank_settlement",
                identity,
            )
            repo.update("bank_contracts", {"_id": identity}, {"$set": {"status": "settled"}})

        repository.transaction(settle)
    repository.update_many(
        "sponsor_contracts",
        {"status": "active", "ends_at": {"$lte": now}},
        {"$set": {"status": "expired"}},
    )
