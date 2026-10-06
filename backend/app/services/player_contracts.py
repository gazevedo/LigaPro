"""Professional contracts, game-month payroll and free-agent recruitment."""

from datetime import timedelta
from math import floor

from bson import ObjectId
from fastapi import HTTPException

from app.config.economy import EconomyConfig
from app.config.game import GameConfig
from app.config.team_performance import MoraleConfig
from app.models.game import public, utcnow
from app.services.chemistry import ChemistryService
from app.services.market_value import MarketValueService
from app.services.player_morale import PlayerMoraleService
from app.services.salary import SalaryService

OPEN_STATUSES = ["active", "expiring"]


class ContractService:
    def __init__(self, repository):
        self.repo = repository

    @staticmethod
    def history(repo, contract, action, now, **extra):
        repo.insert(
            "contract_history",
            {
                "_id": ObjectId(),
                "contract_id": contract["_id"],
                "player_id": contract["player_id"],
                "club_id": contract["club_id"],
                "action": action,
                "salary": contract["salary"],
                "expires_at": contract["expires_at"],
                "created_at": now,
                **extra,
            },
        )

    @staticmethod
    def document(player_id, club_id, salary, seasons, config, now):
        period = timedelta(days=config.SEASON_DURATION_DAYS) / 12
        return {
            "_id": ObjectId(),
            "player_id": player_id,
            "club_id": club_id,
            "salary": salary,
            "started_at": now,
            "expires_at": now + timedelta(days=config.SEASON_DURATION_DAYS * seasons),
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "salary_period_seconds": period.total_seconds(),
            "paid_until": now,
            "next_salary_at": now + period,
            "expiring_at": now + timedelta(days=config.SEASON_DURATION_DAYS * seasons) - period,
        }

    @classmethod
    def initial(cls, repo, players, config=None, now=None):
        config, now = config or GameConfig.from_rules(repo.rules()), now or utcnow()
        salaries = (
            SalaryService.normalize(players, EconomyConfig.from_rules(repo.rules()))
            if len(players) == 25
            else [SalaryService.reference(p) for p in players]
        )
        contracts = [
            cls.document(
                p["_id"],
                p["owner_club_id"],
                salaries[index],
                2,
                config,
                now,
            )
            for index, p in enumerate(players)
        ]
        if contracts:
            repo.insert_many("player_contracts", contracts)
            repo.insert_many(
                "contract_history",
                [
                    {
                        "_id": ObjectId(),
                        "contract_id": c["_id"],
                        "player_id": c["player_id"],
                        "club_id": c["club_id"],
                        "action": "created",
                        "salary": c["salary"],
                        "expires_at": c["expires_at"],
                        "created_at": now,
                    }
                    for c in contracts
                ],
            )
        for contract in contracts:
            repo.update(
                "players",
                {"_id": contract["player_id"]},
                {
                    "$set": {
                        "salary": contract["salary"],
                        "contract_status": contract["status"],
                        "contract_expires_at": contract["expires_at"],
                    }
                },
            )
        for club_id in {c["club_id"] for c in contracts}:
            repo.update(
                "club_finances",
                {"_id": club_id},
                {"$set": {"monthly_payroll": cls.payroll(repo, club_id)}},
            )
        return contracts

    def bootstrap(self):
        def operation(repo):
            known = {c["player_id"] for c in repo.many("player_contracts", {}, limit=None)}
            players = repo.many(
                "players",
                {"status": {"$nin": ["retired", "free_agent"]}, "owner_club_id": {"$ne": None}},
                limit=None,
            )
            missing = [p for p in players if p["_id"] not in known]
            for club_id in {p["owner_club_id"] for p in missing}:
                if not repo.find("club_finances", {"_id": club_id}):
                    repo.insert("club_finances", {"_id": club_id, "balance": 0})
            self.initial(repo, missing)

        self.repo.transaction(operation)

    @staticmethod
    def current(repo, player_id):
        return repo.find(
            "player_contracts", {"player_id": player_id, "status": {"$in": OPEN_STATUSES}}
        )

    @staticmethod
    def payroll(repo, club_id):
        contracts = repo.many(
            "player_contracts", {"club_id": club_id, "status": {"$in": OPEN_STATUSES}}, limit=None
        )
        total = sum(c["salary"] for c in contracts)
        loans = repo.many(
            "player_loans",
            {"status": "active", "$or": [{"owner_club_id": club_id}, {"current_club_id": club_id}]},
            limit=None,
        )
        for loan in loans:
            current = ContractService.current(repo, loan["player_id"])
            if current:
                share = round(current["salary"] * loan.get("salary_share", 0))
                total += share if loan["current_club_id"] == club_id else -share
        return total

    @classmethod
    def capacity(cls, repo, club_id, salary, replaced_salary=0):
        balance = repo.find("club_finances", {"_id": club_id})["balance"]
        if balance < cls.payroll(repo, club_id) - replaced_salary + salary:
            raise HTTPException(409, "Saldo insuficiente para a nova folha mensal.")

    @classmethod
    def settle_salary(cls, repo, contract, until):
        until = min(until, contract["expires_at"])
        if until <= contract["paid_until"]:
            return
        start = contract["paid_until"]
        cursor = start
        period = timedelta(seconds=contract["salary_period_seconds"])
        paid = 0
        loans = repo.many(
            "player_loans",
            {
                "player_id": contract["player_id"],
                "owner_club_id": contract["club_id"],
                "starts_at": {"$lt": until},
                "ends_at": {"$gt": start},
            },
            limit=None,
        )
        while cursor < until:
            completed = floor(
                (cursor - contract["started_at"]).total_seconds() / period.total_seconds()
            )
            boundary = contract["started_at"] + (completed + 1) * period
            boundaries = [
                date
                for loan in loans
                for date in (loan["starts_at"], loan["ends_at"])
                if cursor < date < min(until, boundary)
            ]
            end = min([until, boundary, *boundaries])
            cumulative = round(
                contract["salary"] * (end - start).total_seconds() / period.total_seconds()
            )
            amount = cumulative - paid
            if amount:
                loan = next(
                    (item for item in loans if item["starts_at"] <= cursor < item["ends_at"]), None
                )
                share = round(amount * loan.get("salary_share", 0)) if loan else 0
                allocations = [(contract["club_id"], amount - share)]
                if share:
                    allocations.append((loan["current_club_id"], share))
                for payer, cost in allocations:
                    if cost:
                        repo.money(
                            payer,
                            -cost,
                            "salary",
                            contract["_id"],
                            allow_overdraft=EconomyConfig.from_rules(
                                repo.rules()
                            ).ALLOW_NEGATIVE_CASH,
                            effective_at=end - timedelta(microseconds=1),
                        )
                cls.history(
                    repo,
                    contract,
                    "salary_paid",
                    utcnow(),
                    amount=amount,
                    period_start=cursor,
                    period_end=end,
                )
            paid = cumulative
            cursor = end
        repo.update(
            "player_contracts",
            {"_id": contract["_id"]},
            {"$set": {"paid_until": until, "updated_at": utcnow()}},
        )
        contract["paid_until"] = until

    @classmethod
    def terminate(cls, repo, player_id, now=None, reason="terminated"):
        contract = cls.current(repo, player_id)
        if contract:
            now = now or utcnow()
            cls.settle_salary(repo, contract, now)
            repo.update(
                "player_contracts",
                {"_id": contract["_id"]},
                {"$set": {"status": "terminated", "ended_at": now, "updated_at": now}},
            )
            cls.history(repo, contract, "terminated", now, reason=reason)
            repo.update(
                "players",
                {"_id": player_id},
                {"$set": {"salary": 0, "contract_status": "terminated"}},
            )
        return contract

    def get(self, user, identity):
        club, player = self.repo.owned(user.id), self.repo.document("players", identity)
        if player["owner_club_id"] != club["_id"]:
            raise HTTPException(403, "Contrato de jogador de outro clube.")
        return public(
            {
                "contract": self.current(self.repo, player["_id"]),
                "history": self.repo.many(
                    "contract_history",
                    {"player_id": player["_id"], "club_id": club["_id"]},
                    limit=None,
                    sort=[("created_at", -1)],
                ),
            }
        )

    def renew(self, user, identity, data):
        def operation(repo):
            now = utcnow()
            club, player = repo.owned(user.id), repo.document("players", identity)
            if player["owner_club_id"] != club["_id"]:
                raise HTTPException(403, "Só é possível renovar jogadores próprios.")
            repo.update("clubs", {"_id": club["_id"]}, {"$inc": {"roster_revision": 1}})
            current = self.current(repo, player["_id"])
            if (
                not current
                or current["club_id"] != club["_id"]
                or current["expires_at"] <= now
                or player.get("status") == "retired"
            ):
                raise HTTPException(409, "Contrato indisponível para renovação.")
            self.settle_salary(repo, current, now)
            self.capacity(repo, club["_id"], data.salary, current["salary"])
            self.terminate(repo, player["_id"], now, "renewed")
            contract = self.document(
                player["_id"],
                club["_id"],
                data.salary,
                data.seasons,
                GameConfig.from_rules(repo.rules()),
                now,
            )
            repo.insert("player_contracts", contract)
            self.history(repo, contract, "renewed", now, previous_contract_id=current["_id"])
            repo.update(
                "players",
                {"_id": player["_id"]},
                {
                    "$set": {
                        "salary": contract["salary"],
                        "contract_status": "active",
                        "contract_expires_at": contract["expires_at"],
                    }
                },
            )
            MarketValueService().recalculate(repo, [player], "renewal", now=now)
            return public(contract)

        return self.repo.transaction(operation)

    def sign(self, user, identity, data):
        def operation(repo):
            from app.services.competition import CompetitionService

            CompetitionService.require_transfer_window(repo)
            club, player = repo.owned(user.id), repo.document("players", identity)
            return self.sign_for_club(repo, club, player, data.salary, data.seasons)

        return self.repo.transaction(operation)

    @classmethod
    def sign_for_club(cls, repo, club, player, salary, seasons, now=None):
        if (
            player.get("status") == "retired"
            or player.get("owner_club_id") is not None
            or player.get("current_club_id") is not None
            or cls.current(repo, player["_id"])
        ):
            raise HTTPException(409, "Jogador não está livre.")
        repo.update("clubs", {"_id": club["_id"]}, {"$inc": {"roster_revision": 1}})
        cls.capacity(repo, club["_id"], salary)
        from app.services.negotiation import PlayerContractDecisionService

        decision = PlayerContractDecisionService.evaluate(player, club, salary, seasons * 12)
        if not decision["accepted"]:
            raise HTTPException(409, decision["reason"])
        now = now or utcnow()
        contract = cls.document(
            player["_id"],
            club["_id"],
            salary,
            seasons,
            GameConfig.from_rules(repo.rules()),
            now,
        )
        repo.insert("player_contracts", contract)
        repo.update(
            "players",
            {"_id": player["_id"]},
            {
                "$set": {
                    "status": player.get("status", "available")
                    if player.get("status") in {"injured", "suspended"}
                    else "available",
                    "salary": salary,
                    "contract_status": "active",
                    "contract_expires_at": contract["expires_at"],
                    "joined_at": now,
                    "owner_club_id": club["_id"],
                    "current_club_id": club["_id"],
                }
            },
        )
        repo.update("lineups", {"_id": club["_id"]}, {"$addToSet": {"reserves": player["_id"]}})
        ChemistryService().recruit(repo, club["_id"])
        PlayerMoraleService().change(repo, player, MoraleConfig().transfer)
        cls.history(repo, contract, "signed", now)
        repo.event(club["_id"], "transfer", "Contratação de jogador livre", reference=player["_id"])
        MarketValueService().recalculate(
            repo, [repo.find("players", {"_id": player["_id"]})], "transfer"
        )
        return public(contract)

    @classmethod
    def transfer(cls, repo, player_id, buyer_id, salary=None, months=None, now=None):
        now = now or utcnow()
        current = cls.current(repo, player_id)
        if not current or current["expires_at"] <= now:
            raise HTTPException(409, "Jogador sem contrato vigente.")
        salary = current["salary"] if salary is None else salary
        cls.capacity(repo, buyer_id, salary)
        cls.terminate(repo, player_id, now, "transfer")
        contract = cls.document(
            player_id, buyer_id, salary, 1, GameConfig.from_rules(repo.rules()), now
        )
        contract["expires_at"] = (
            current["expires_at"]
            if months is None
            else now + timedelta(seconds=current["salary_period_seconds"] * months)
        )
        contract["salary_period_seconds"] = current["salary_period_seconds"]
        contract["expiring_at"] = contract["expires_at"] - timedelta(
            seconds=contract["salary_period_seconds"]
        )
        contract["next_salary_at"] = now + timedelta(seconds=contract["salary_period_seconds"])
        repo.insert("player_contracts", contract)
        repo.update(
            "players",
            {"_id": player_id},
            {
                "$set": {
                    "salary": salary,
                    "contract_status": "active",
                    "contract_expires_at": contract["expires_at"],
                    "player_transfer_status": "not_for_sale",
                }
            },
        )
        cls.history(repo, contract, "transferred", now, previous_contract_id=current["_id"])

    @classmethod
    def expire(cls, repo, contract, now):
        player = repo.find("players", {"_id": contract["player_id"]})
        from app.services.live_match import busy_clubs

        if player and player.get("current_club_id") in busy_clubs(repo):
            return
        cls.settle_salary(repo, contract, contract["expires_at"])
        repo.update(
            "player_contracts",
            {"_id": contract["_id"]},
            {"$set": {"status": "expired", "updated_at": now}},
        )
        cls.history(repo, contract, "expired", now)
        if not player or player.get("status") == "retired":
            return
        clubs = {
            identity
            for identity in (player["owner_club_id"], player["current_club_id"])
            if identity is not None
        }
        for club_id in sorted(clubs):
            repo.update("clubs", {"_id": club_id}, {"$inc": {"roster_revision": 1}})
            repo.update(
                "lineups",
                {"_id": club_id},
                {"$pull": {"starters": player["_id"], "reserves": player["_id"]}},
            )
        repo.update(
            "players",
            {"_id": player["_id"]},
            {
                "$set": {
                    "status": player.get("status")
                    if player.get("status") in {"injured", "suspended"}
                    else "available",
                    "owner_club_id": None,
                    "current_club_id": None,
                    "player_transfer_status": "available",
                    "contract_status": "expired",
                    "contract_expires_at": contract["expires_at"],
                    "salary": 0,
                }
            },
        )
        repo.update_many(
            "player_loans",
            {"player_id": player["_id"], "status": "active"},
            {"$set": {"status": "expired"}},
        )
        listings = repo.many(
            "transfer_listings", {"player_id": player["_id"], "status": "active"}, limit=None
        )
        repo.update_many(
            "transfer_listings",
            {"player_id": player["_id"], "status": "active"},
            {"$set": {"status": "closed"}},
        )
        repo.update_many(
            "transfer_offers",
            {
                "listing_id": {"$in": [item["_id"] for item in listings]},
                "status": {"$in": ["pending", "counter_offer", "player_accepted"]},
            },
            {"$set": {"status": "closed"}},
        )
        MarketValueService().recalculate(
            repo, [repo.find("players", {"_id": player["_id"]})], "expiry", now=now
        )
        from app.services.game import MarketService

        for club_id in clubs:
            try:
                MarketService.repair_lineup(repo, club_id)
            except HTTPException as exc:
                if exc.status_code != 409:
                    raise
            repo.event(club_id, "transfer", "Fim de contrato", now, player["_id"])

    def process_due(self, now=None):
        now = now or utcnow()
        # A game month uses the duration captured when this contract was signed.
        for contract in self.repo.many(
            "player_contracts",
            {
                "status": {"$in": OPEN_STATUSES},
                "$or": [
                    {"next_salary_at": {"$lte": now}},
                    {"expires_at": {"$lte": now}},
                    {"status": "active", "expiring_at": {"$lte": now}},
                ],
            },
            limit=None,
        ):
            if contract["next_salary_at"] > now and contract["expires_at"] > now + timedelta(
                seconds=contract["salary_period_seconds"]
            ):
                continue

            def operation(repo, identity=contract["_id"]):
                current = repo.find(
                    "player_contracts", {"_id": identity, "status": {"$in": OPEN_STATUSES}}
                )
                if not current:
                    return
                repo.update("clubs", {"_id": current["club_id"]}, {"$inc": {"roster_revision": 1}})
                period = timedelta(seconds=current["salary_period_seconds"])
                if current["expires_at"] <= now:
                    self.expire(repo, current, now)
                    return
                completed = floor(
                    (now - current["started_at"]).total_seconds() / period.total_seconds()
                )
                until = current["started_at"] + completed * period
                if until > current["paid_until"]:
                    self.settle_salary(repo, current, until)
                status = "expiring" if current["expires_at"] <= now + period else current["status"]
                changes = {
                    "next_salary_at": max(current["paid_until"], current["started_at"]) + period,
                    "status": status,
                    "updated_at": now,
                }
                repo.update("player_contracts", {"_id": identity}, {"$set": changes})
                repo.update(
                    "players",
                    {"_id": current["player_id"]},
                    {
                        "$set": {
                            "contract_status": status,
                            "contract_expires_at": current["expires_at"],
                            "salary": current["salary"],
                        }
                    },
                )
                if status != current["status"]:
                    self.history(repo, current, "expiring", now)

            self.repo.transaction(operation)

    def finance(self, club_id):
        contracts = self.repo.many(
            "player_contracts", {"club_id": club_id, "status": {"$in": OPEN_STATUSES}}, limit=None
        )
        players = {
            p["_id"]: p
            for p in self.repo.many(
                "players", {"_id": {"$in": [c["player_id"] for c in contracts]}}, limit=None
            )
        }
        now = utcnow()
        return {
            "monthly_payroll": sum(c["salary"] for c in contracts),
            "total_contract_cost": sum(
                round(
                    c["salary"]
                    * max(0, (c["expires_at"] - max(now, c["paid_until"])).total_seconds())
                    / c["salary_period_seconds"]
                )
                for c in contracts
            ),
            "salary_costs": [
                {
                    "player_id": str(c["player_id"]),
                    "name": players.get(c["player_id"], {}).get("name", "Jogador"),
                    "salary": c["salary"],
                    "expires_at": c["expires_at"],
                    "status": c["status"],
                }
                for c in contracts
            ],
            "salary_history": self.repo.many(
                "financial_transactions",
                {"club_id": club_id, "category": {"$in": ["player_salary", "salary"]}},
                sort=[("created_at", -1)],
            ),
        }
