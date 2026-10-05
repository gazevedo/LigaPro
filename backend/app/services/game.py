from collections import Counter
from datetime import timedelta

from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.config.game import GameConfig, legacy_position
from app.models.game import FACILITIES, public, utcnow
from app.services.competition import CompetitionService
from app.services.player_contracts import ContractService
from app.services.player_development import PlayerGeneratorService
from app.services.tactics import TacticsService


class ClubService:
    def __init__(self, repository):
        self.repo = repository

    def status(self, user):
        club = self.repo.find("clubs", {"owner_user_id": ObjectId(user.id)})
        return {"club": self.response(club) if club else None}

    def catalog(self):
        return public(
            {
                "countries": self.repo.many("countries", {}),
                "badges": self.repo.many("club_badges", {}),
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
                ]
            }
        )

    def create(self, user, data):
        CompetitionService.ensure_lock(self.repo)

        def operation(repo):
            CompetitionService.lock(repo)
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
                    **data.model_dump(),
                    "country": public(country),
                    "badge": public(badge),
                    "created_at": now,
                    "ranking": 0,
                    "competition_positions": [],
                    "trophies": [],
                },
            )
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
                    "capacity": rules["initial_capacity"],
                    "ticket_price": rules["ticket_price"],
                    "facilities": {key: 1 for key in FACILITIES},
                },
            )
            repo.insert("club_finances", {"_id": club_id, "balance": 0})
            repo.money(club_id, rules["initial_balance"], "initial_funding")
            repo.insert(
                "sponsor_contracts",
                {
                    "_id": ObjectId(),
                    "club_id": club_id,
                    "name": "Parceiro inicial",
                    "status": "active",
                    "value": rules["sponsor_value"],
                    "starts_at": now,
                    "ends_at": now + timedelta(days=rules["sponsor_days"]),
                },
            )
            repo.money(club_id, rules["sponsor_value"], "sponsor")
            ContractService.initial(repo, players, GameConfig.from_rules(rules), now)
            competition = CompetitionService(repo)
            competition.enroll(repo, club, now)
            season = competition.current(repo)
            competition.generate_youth(repo, club, season, competition.season_config(season))
            return self.response(club)

        try:
            return self.repo.transaction(operation)
        except DuplicateKeyError as exc:
            raise HTTPException(409, "Você já possui um clube.") from exc


class SquadService:
    def __init__(self, repository):
        self.repo = repository

    def get(self, user):
        club = self.repo.owned(user.id)
        return public(
            {
                "players": self.repo.many(
                    "players",
                    {"current_club_id": club["_id"], "status": {"$ne": "retired"}},
                    limit=None,
                ),
                "lineup": self.repo.find("lineups", {"_id": club["_id"]}),
                "formations": self.repo.rules()["formations"],
            }
        )

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
            if set(ids) != {str(p["_id"]) for p in players}:
                raise HTTPException(
                    422, "Escalação deve incluir exatamente os jogadores do plantel."
                )
            positions = Counter(
                legacy_position(p["position"]) for p in players if str(p["_id"]) in data.starters
            )
            if dict(positions) != {"GOL": 1, **formation}:
                raise HTTPException(
                    422, "Titulares incompatíveis com a formação; é necessário um goleiro."
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
        stadium = self.repo.find("stadiums", {"_id": self.repo.owned(user.id)["_id"]})
        return public(
            {
                **stadium,
                "names": FACILITIES,
                "upgrade_costs": {
                    key: level * self.repo.rules()["upgrade_base_cost"]
                    for key, level in stadium["facilities"].items()
                },
            }
        )

    def upgrade(self, user, facility):
        if facility not in FACILITIES:
            raise HTTPException(404, "Construção não encontrada.")

        def operation(repo):
            club = repo.owned(user.id)
            stadium = repo.find("stadiums", {"_id": club["_id"]})
            cost = stadium["facilities"][facility] * repo.rules()["upgrade_base_cost"]
            repo.money(club["_id"], -cost, "stadium_upgrade")
            increments = {f"facilities.{facility}": 1}
            if facility == "stands":
                increments["capacity"] = 1000
            repo.update("stadiums", {"_id": club["_id"]}, {"$inc": increments})
            repo.event(club["_id"], "stadium", FACILITIES[facility])

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
        return public(
            {
                "price": stadium["ticket_price"],
                "capacity": stadium["capacity"],
                "history": self.repo.many("ticket_history", {"club_id": club["_id"]}),
                "income": self.repo.ticket_income(club["_id"]),
            }
        )

    def ticket_price(self, user, price):
        club = self.repo.owned(user.id)
        self.repo.update("stadiums", {"_id": club["_id"]}, {"$set": {"ticket_price": price}})
        return self.tickets(user)

    def sponsors(self, user):
        club, rules = self.repo.owned(user.id), self.repo.rules()
        return public(
            {
                "contracts": self.repo.many("sponsor_contracts", {"club_id": club["_id"]}),
                "offers": [
                    {
                        "id": "principal",
                        "name": "Parceiro principal",
                        "required_ranking": 0,
                        "duration_days": rules["sponsor_days"],
                        "value": rules["sponsor_value"],
                    }
                ],
            }
        )

    def sponsor(self, user, identity):
        if identity != "principal":
            raise HTTPException(404, "Oferta não encontrada.")

        def operation(repo):
            club, now, rules = repo.owned(user.id), utcnow(), repo.rules()
            repo.update_many(
                "sponsor_contracts",
                {"club_id": club["_id"], "status": "active", "ends_at": {"$lte": now}},
                {"$set": {"status": "expired"}},
            )
            # Serialize all contracts of this club.
            repo.update("clubs", {"_id": club["_id"]}, {"$inc": {"sponsor_revision": 1}})
            if repo.find("sponsor_contracts", {"club_id": club["_id"], "status": "active"}):
                raise HTTPException(409, "Já existe patrocinador principal ativo.")
            contract = repo.insert(
                "sponsor_contracts",
                {
                    "_id": ObjectId(),
                    "club_id": club["_id"],
                    "name": "Parceiro principal",
                    "status": "active",
                    "value": rules["sponsor_value"],
                    "starts_at": now,
                    "ends_at": now + timedelta(days=rules["sponsor_days"]),
                },
            )
            repo.money(club["_id"], rules["sponsor_value"], "sponsor", contract["_id"])
            return public(contract)

        return self.repo.transaction(operation)


class CalendarService:
    def __init__(self, repository):
        self.repo = repository

    def get(self, user, filters):
        query = {"club_id": self.repo.owned(user.id)["_id"]}
        if filters.type:
            query["type"] = filters.type
        dates = {}
        if filters.start:
            dates["$gte"] = filters.start
        if filters.end:
            dates["$lte"] = filters.end
        if filters.start and filters.end and filters.start > filters.end:
            raise HTTPException(422, "Período inválido.")
        if dates:
            query["date"] = dates
        return public(self.repo.many("calendar_events", query, limit=500, sort=[("date", 1)]))


class MarketService:
    def __init__(self, repository):
        self.repo = repository

    def player(self, identity):
        player = self.repo.document("players", identity)
        listing = self.repo.find(
            "transfer_listings", {"player_id": player["_id"], "status": "active"}
        )
        return public({**player, "listing": listing})

    def search(self, filters):
        query = {"status": {"$ne": "retired"}}
        for key in ["position", "country_id", "status"]:
            if filters.get(key):
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
        return public(self.repo.search_players(query, filters.get("type")))

    def mine(self, user):
        club = self.repo.owned(user.id)
        listings = self.repo.many("transfer_listings", {"seller_club_id": club["_id"]})
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
        def operation(repo):
            club, player = repo.owned(user.id), repo.document("players", data.player_id)
            if player["owner_club_id"] != club["_id"] or player["current_club_id"] != club["_id"]:
                raise HTTPException(
                    403, "Só é possível anunciar jogadores próprios e presentes no clube."
                )
            if player.get("status") == "retired":
                raise HTTPException(409, "Jogador aposentado.")
            lineup = repo.find("lineups", {"_id": club["_id"]})
            if player["_id"] in lineup["starters"]:
                raise HTTPException(409, "Mova o jogador para a reserva antes de anunciá-lo.")
            repo.update("clubs", {"_id": club["_id"]}, {"$inc": {"roster_revision": 1}})
            return public(
                repo.insert(
                    "transfer_listings",
                    {
                        "_id": ObjectId(),
                        "player_id": player["_id"],
                        "seller_club_id": club["_id"],
                        "type": data.type,
                        "price": data.price,
                        "duration_days": data.duration_days,
                        "status": "active",
                        "created_at": utcnow(),
                    },
                )
            )

        try:
            return self.repo.transaction(operation)
        except DuplicateKeyError as exc:
            raise HTTPException(409, "Jogador já anunciado.") from exc

    def offer(self, user, data):
        def operation(repo):
            club, listing = repo.owned(user.id), repo.document("transfer_listings", data.listing_id)
            if listing["status"] != "active" or listing["seller_club_id"] == club["_id"]:
                raise HTTPException(409, "Anúncio indisponível ou do próprio clube.")
            if repo.find("club_finances", {"_id": club["_id"]})["balance"] < data.amount:
                raise HTTPException(409, "Saldo insuficiente.")
            repo.update("transfer_listings", {"_id": listing["_id"]}, {"$inc": {"revision": 1}})
            if repo.find(
                "transfer_offers",
                {"listing_id": listing["_id"], "buyer_club_id": club["_id"], "status": "pending"},
            ):
                raise HTTPException(409, "Já existe proposta pendente deste clube.")
            return public(
                repo.insert(
                    "transfer_offers",
                    {
                        "_id": ObjectId(),
                        "listing_id": listing["_id"],
                        "seller_club_id": listing["seller_club_id"],
                        "buyer_club_id": club["_id"],
                        "amount": data.amount,
                        "status": "pending",
                        "created_at": utcnow(),
                    },
                )
            )

        return self.repo.transaction(operation)

    @staticmethod
    def repair_lineup(repo, club_id):
        players = repo.many(
            "players", {"current_club_id": club_id, "status": {"$ne": "retired"}}, limit=None
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
        def operation(repo):
            CompetitionService.require_transfer_window(repo)
            club, offer = repo.owned(user.id), repo.document("transfer_offers", identity)
            listing = repo.document("transfer_listings", str(offer["listing_id"]))
            if offer["seller_club_id"] != club["_id"]:
                raise HTTPException(403, "Proposta de outro clube.")
            if offer["status"] != "pending" or listing["status"] != "active":
                raise HTTPException(409, "Proposta ou anúncio encerrado.")
            player = repo.document("players", str(listing["player_id"]))
            if player["owner_club_id"] != club["_id"] or player["current_club_id"] != club["_id"]:
                raise HTTPException(409, "Jogador indisponível.")
            if player.get("status") == "retired":
                raise HTTPException(409, "Jogador aposentado.")
            contract = ContractService.current(repo, player["_id"])
            if not contract or contract["expires_at"] <= utcnow():
                raise HTTPException(409, "Jogador sem contrato vigente.")
            # Lock both rosters; simultaneous lineup/transfer changes are retried by MongoDB.
            for club_id in sorted([club["_id"], offer["buyer_club_id"]]):
                repo.update("clubs", {"_id": club_id}, {"$inc": {"roster_revision": 1}})
            repo.money(
                offer["buyer_club_id"],
                -offer["amount"],
                "player_purchase" if listing["type"] == "sale" else "player_loan",
                offer["_id"],
            )
            repo.money(
                club["_id"],
                offer["amount"],
                "player_sale" if listing["type"] == "sale" else "player_loan_income",
                offer["_id"],
            )
            ownership = {"current_club_id": offer["buyer_club_id"]}
            if listing["type"] == "sale":
                ContractService.transfer(repo, player["_id"], offer["buyer_club_id"])
                ownership["owner_club_id"] = offer["buyer_club_id"]
            else:
                loan = repo.insert(
                    "player_loans",
                    {
                        "_id": ObjectId(),
                        "player_id": player["_id"],
                        "owner_club_id": club["_id"],
                        "current_club_id": offer["buyer_club_id"],
                        "starts_at": utcnow(),
                        "ends_at": utcnow() + timedelta(days=listing["duration_days"]),
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
                self.repair_lineup(repo, club_id)
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
                    "created_at": utcnow(),
                },
            )
            repo.update(
                "transfer_listings", {"_id": listing["_id"]}, {"$set": {"status": "closed"}}
            )
            repo.update_many(
                "transfer_offers",
                {"listing_id": listing["_id"], "status": "pending"},
                {"$set": {"status": "closed"}},
            )
            return public(
                repo.update(
                    "transfer_offers", {"_id": offer["_id"]}, {"$set": {"status": "accepted"}}
                )
            )

        return self.repo.transaction(operation)

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
            if document["status"] != status:
                raise HTTPException(409, "Negociação já encerrada.")
            repo.update(collection, {"_id": document["_id"]}, {"$set": {"status": "cancelled"}})
            if collection == "transfer_listings":
                repo.update_many(
                    "transfer_offers",
                    {"listing_id": document["_id"], "status": "pending"},
                    {"$set": {"status": "closed"}},
                )
            return {"status": "cancelled"}

        return self.repo.transaction(operation)


def process_due(repository):
    now = utcnow()
    CompetitionService(repository).process_due(now)
    ContractService(repository).process_due(now)
    for loan in repository.many("player_loans", {"status": "active", "ends_at": {"$lte": now}}):

        def return_player(repo, identity=loan["_id"]):
            current = repo.find("player_loans", {"_id": identity, "status": "active"})
            if not current:
                return
            for club_id in sorted([current["owner_club_id"], current["current_club_id"]]):
                repo.update("clubs", {"_id": club_id}, {"$inc": {"roster_revision": 1}})
            repo.update(
                "players",
                {"_id": current["player_id"]},
                {"$set": {"current_club_id": current["owner_club_id"]}},
            )
            for club_id in [current["owner_club_id"], current["current_club_id"]]:
                MarketService.repair_lineup(repo, club_id)
                repo.event(club_id, "transfer", "Retorno de empréstimo", reference=identity)
            repo.update("player_loans", {"_id": identity}, {"$set": {"status": "returned"}})

        repository.transaction(return_player)
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
