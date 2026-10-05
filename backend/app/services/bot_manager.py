"""Bots use the same contracts, market settlement, training and club ledger."""

from datetime import timedelta

from bson import ObjectId
from fastapi import HTTPException

from app.config.economy import EconomyConfig
from app.config.game import GameConfig, legacy_position
from app.models.game import utcnow
from app.schemas.game import CounterOfferInput, ListingInput, NegotiationInput
from app.services.market_value import MarketValueService
from app.services.match_engine import (
    BOT_PRESETS,
    bot_preset,
)
from app.services.negotiation import NegotiationService
from app.services.player_contracts import ContractService
from app.services.player_development import TrainingService
from app.services.salary import SalaryService
from app.services.tactics import TacticsService


def audit(repo, club_id, kind, payload, reason, now):
    repo.insert(
        "bot_decisions",
        {
            "_id": ObjectId(),
            "club_id": club_id,
            "decision_type": kind,
            "payload": payload,
            "reason": reason,
            "created_at": now,
        },
    )


class BotFinanceService:
    @staticmethod
    def budget(repo, club_id):
        cash = repo.find("club_finances", {"_id": club_id})["balance"]
        payroll = ContractService.payroll(repo, club_id)
        config = EconomyConfig.from_rules(repo.rules())
        return max(0, cash - max(2 * payroll, config.fixed_revenue))

    @staticmethod
    def affordable(repo, club_id, fee, salary):
        config = EconomyConfig.from_rules(repo.rules())
        return (
            fee <= BotFinanceService.budget(repo, club_id)
            and ContractService.payroll(repo, club_id) + salary <= config.fixed_revenue * 1.2
        )


class BotLineupService:
    @staticmethod
    def choose(repo, club, now):
        players = repo.many(
            "players",
            {
                "current_club_id": club["_id"],
                "status": {"$nin": ["retired", "injured", "suspended"]},
            },
            limit=None,
        )
        if len(players) < 11:
            return None
        old = repo.find("lineups", {"_id": club["_id"]})
        rules = repo.rules()["formations"]
        by_position = {
            role: sorted(
                [p for p in players if legacy_position(p["position"]) == role],
                key=lambda p: (
                    -(
                        p["strength"]
                        * (0.7 + 0.3 * p.get("physical_condition", 100) / 100)
                        * (0.7 + 0.3 * p.get("energy", 100) / 100)
                    )
                ),
            )
            for role in ("GOL", "DEF", "MED", "ATA")
        }
        for formation in [old["formation"], *rules]:
            selected = []
            for role, count in {"GOL": 1, **rules[formation]}.items():
                if len(by_position[role]) < count:
                    break
                selected.extend(by_position[role][:count])
            if len(selected) != 11:
                continue
            changes = {
                "formation": formation,
                "starters": [p["_id"] for p in selected],
                "reserves": [p["_id"] for p in players if p not in selected],
            }
            if any(old.get(key) != value for key, value in changes.items()):
                from app.services.chemistry import ChemistryService

                ChemistryService().lineup_change(
                    repo, club["_id"], old, changes["starters"], formation
                )
                repo.update("lineups", {"_id": club["_id"]}, {"$set": changes})
                audit(
                    repo,
                    club["_id"],
                    "lineup",
                    {"formation": formation, "starters": changes["starters"]},
                    "Força e condição, com jogadores disponíveis em suas posições.",
                    now,
                )
            return changes
        # Scarce squads may improvise, with the same engine position-fit penalty as humans.
        strongest = sorted(
            players, key=lambda p: -p["strength"] * p.get("physical_condition", 100)
        )[:11]
        keepers = [p for p in players if p["position"] == "GK"]
        if not keepers:
            return None
        strongest = [keepers[0]] + [p for p in strongest if p["_id"] != keepers[0]["_id"]][:10]
        if len(strongest) < 11:
            return None
        changes = {
            "formation": "4-4-2",
            "starters": [p["_id"] for p in strongest],
            "reserves": [p["_id"] for p in players if p not in strongest],
        }
        repo.update("lineups", {"_id": club["_id"]}, {"$set": changes})
        return changes


class BotTacticsService:
    @staticmethod
    def choose(repo, club, lineup, now):
        own = repo.many("players", {"_id": {"$in": lineup["starters"]}}, limit=None)
        next_game = repo.many(
            "matches",
            {
                "status": "scheduled",
                "date": {"$gte": now},
                "$or": [{"home_club_id": club["_id"]}, {"away_club_id": club["_id"]}],
            },
            limit=1,
            sort=[("date", 1)],
        )
        rival = []
        if next_game:
            match = next_game[0]
            opponent = (
                match["away_club_id"]
                if match["home_club_id"] == club["_id"]
                else match["home_club_id"]
            )
            opposing = repo.find("lineups", {"_id": opponent})
            if opposing:
                rival = repo.many("players", {"_id": {"$in": opposing["starters"]}}, limit=None)
        own_strength = sum(p["strength"] for p in own) / max(1, len(own))
        rival_strength = (
            sum(p["strength"] for p in rival) / max(1, len(rival)) if rival else own_strength
        )
        preset = (
            "counter"
            if own_strength < rival_strength - 5
            else "aggressive"
            if own_strength > rival_strength + 10
            else "balanced"
        )
        style, marking, focus = BOT_PRESETS[preset]
        if sum(p.get("physical_condition", 100) for p in own) / len(own) < 70:
            style, marking = "counter_attack", "light"
        changes = {
            "formation": lineup["formation"],
            "play_style": style,
            "marking": marking,
            "attack_focus": focus,
        }
        old = TacticsService.settings(repo, club["_id"], lineup)
        if any(old.get(key) != value for key, value in changes.items()):
            TacticsService.persist(repo, club["_id"], changes)
            audit(
                repo,
                club["_id"],
                "tactics",
                changes,
                "Comparação visível das forças e da condição do elenco.",
                now,
            )


class BotMatchManager:
    @staticmethod
    def preset(team, opponent, difference):
        return bot_preset(team, opponent, difference)

    @staticmethod
    def replacement_score(outgoing, incoming, card_count, difference):
        return (
            (100 - outgoing.energy)
            + max(0, outgoing.strength - incoming.strength) * -0.2
            + card_count * 20
            + (10 if difference < 0 and outgoing.assigned_position == "ATT" else 0)
        )


class BotContractService:
    @staticmethod
    def manage(repo, club, now):
        lineup = repo.find("lineups", {"_id": club["_id"]})
        contracts = repo.many(
            "player_contracts",
            {
                "club_id": club["_id"],
                "status": {"$in": ["active", "expiring"]},
                "expiring_at": {"$lte": now},
            },
            limit=None,
        )
        for current in contracts:
            player = repo.find("players", {"_id": current["player_id"]})
            if (
                current["expires_at"] <= now
                or not player
                or player["status"] == "retired"
                or player.get("current_club_id") != club["_id"]
            ):
                continue
            important = (
                player["_id"] in lineup["starters"]
                or player["age"] < 28
                or player["position"] == "GK"
            )
            if not important or current["salary"] > SalaryService.reference(player) * 1.8:
                continue
            if BotFinanceService.budget(repo, club["_id"]) < current["salary"]:
                continue
            ContractService.terminate(repo, player["_id"], now, "renewed")
            renewed = ContractService.document(
                player["_id"],
                club["_id"],
                current["salary"],
                2,
                GameConfig.from_rules(repo.rules()),
                now,
            )
            repo.insert("player_contracts", renewed)
            ContractService.history(
                repo, renewed, "renewed", now, previous_contract_id=current["_id"]
            )
            repo.update(
                "players",
                {"_id": player["_id"]},
                {
                    "$set": {
                        "salary": renewed["salary"],
                        "contract_status": "active",
                        "contract_expires_at": renewed["expires_at"],
                    }
                },
            )
            MarketValueService().recalculate(repo, [player], "renewal", now=now)
            audit(
                repo,
                club["_id"],
                "contract",
                {"player_id": player["_id"], "salary": renewed["salary"]},
                "Renovação de jogador importante dentro do orçamento.",
                now,
            )


class BotTrainingService:
    @staticmethod
    def manage(repo, club, now):
        players = repo.many(
            "players", {"current_club_id": club["_id"], "status": "available"}, limit=None
        )
        lineup = repo.find("lineups", {"_id": club["_id"]})
        progress = {
            row["_id"]: row.get("progress", 0)
            for row in repo.many(
                "player_training", {"_id": {"$in": [p["_id"] for p in players]}}, limit=None
            )
        }
        selected = sorted(
            players,
            key=lambda p: (
                -progress.get(p["_id"], 0),
                p["age"],
                p["_id"] not in lineup["starters"],
                str(p["_id"]),
            ),
        )[:3]
        for player in selected:
            try:
                TrainingService.train_for_club(repo, club, str(player["_id"]))
            except HTTPException as exc:
                if exc.status_code != 409:
                    raise
                continue
            audit(
                repo,
                club["_id"],
                "training",
                {"player_id": player["_id"]},
                "Prioridade aos jovens disponíveis e titulares.",
                now,
            )


class BotYouthService:
    @staticmethod
    def manage(repo, club, now):
        youth = repo.many(
            "youth_players",
            {"current_club_id": club["_id"], "status": {"$in": ["available", "active"]}},
            limit=None,
        )
        squad = repo.many(
            "players", {"current_club_id": club["_id"], "status": {"$ne": "retired"}}, limit=None
        )
        for player in youth:
            role = [p for p in squad if p["position"] == player["position"]]
            if (
                player["age"] >= 18
                and BotFinanceService.affordable(
                    repo, club["_id"], 0, SalaryService.reference(player)
                )
                and len(squad) < 30
                and (
                    len(squad) < 25
                    or not role
                    or player["strength"] >= min(p["strength"] for p in role)
                )
            ):
                professional = TrainingService.promote_for_club(repo, club, str(player["_id"]))
                squad.append({**player, "_id": ObjectId(professional["id"])})
                audit(
                    repo,
                    club["_id"],
                    "youth_promotion",
                    {"player_id": player["_id"]},
                    "Júnior em idade de promoção atende uma carência do elenco.",
                    now,
                )
            elif (
                player["age"] >= 21
                and role
                and player["strength"] < min(p["strength"] for p in role) - 15
            ):
                repo.update(
                    "youth_players",
                    {"_id": player["_id"]},
                    {
                        "$set": {
                            "current_club_id": None,
                            "owner_club_id": None,
                            "status": "retired",
                            "retired": True,
                        }
                    },
                )
                audit(
                    repo,
                    club["_id"],
                    "youth_release",
                    {"player_id": player["_id"]},
                    "Júnior sem perspectiva de espaço no elenco.",
                    now,
                )


class BotStadiumService:
    @staticmethod
    def manage(repo, club, now):
        stadium = repo.find("stadiums", {"_id": club["_id"]})
        if not stadium:
            return
        history = repo.many(
            "ticket_history", {"club_id": club["_id"]}, limit=3, sort=[("created_at", -1)]
        )
        if len(history) < 3 or any(h["attendance"] < stadium["capacity"] * 0.9 for h in history):
            return
        cost = stadium.get("facilities", {}).get("stands", 1) * repo.rules()["upgrade_base_cost"]
        if cost > BotFinanceService.budget(repo, club["_id"]):
            return
        from app.services.game import StadiumService

        StadiumService.upgrade_for_club(repo, club, "stands")
        audit(
            repo,
            club["_id"],
            "stadium",
            {"cost": cost},
            "Lotação recorrente e reserva de caixa preservada.",
            now,
        )


class BotTransferService:
    TARGETS = {"GK": 3, "FB": 4, "CB": 4, "MID": 8, "ATT": 6}

    @classmethod
    def manage(cls, repo, club, now):
        from app.services.game import MarketService

        # React to incoming negotiations without changing human approvals.
        for offer in repo.many(
            "transfer_offers",
            {
                "seller_club_id": club["_id"],
                "negotiation_version": 2,
                "status": "pending",
                "expires_at": {"$gt": now},
            },
            limit=None,
        ):
            player = repo.find("players", {"_id": offer["player_id"]})
            if not player or player.get("owner_club_id") != club["_id"]:
                continue
            quote = MarketValueService.asking_price(
                player, "loan_listed" if offer["offer_type"] == "loan" else None
            )
            if offer["amount"] >= quote:
                NegotiationService.approve_for_club(
                    repo, club, str(offer["_id"]), "accept", now=now
                )
            else:
                NegotiationService.approve_for_club(
                    repo,
                    club,
                    str(offer["_id"]),
                    "counter",
                    CounterOfferInput(transfer_value=quote),
                    now,
                )
            audit(
                repo,
                club["_id"],
                "offer_response",
                {"offer_id": offer["_id"]},
                "Avaliação do preço e da disponibilidade do jogador.",
                now,
            )
        for offer in repo.many(
            "transfer_offers",
            {
                "buyer_club_id": club["_id"],
                "negotiation_version": 2,
                "status": {"$in": ["counter_offer", "player_accepted"]},
                "expires_at": {"$gt": now},
            },
            limit=None,
        ):
            if not BotFinanceService.affordable(
                repo, club["_id"], offer["amount"], offer["salary_offer"]
            ):
                repo.update(
                    "transfer_offers", {"_id": offer["_id"]}, {"$set": {"status": "cancelled"}}
                )
                continue
            if offer["status"] == "counter_offer":
                NegotiationService.approve_for_club(
                    repo, club, str(offer["_id"]), "accept_counter", now=now
                )
                offer = repo.find("transfer_offers", {"_id": offer["_id"]})
            if offer["status"] == "player_accepted":
                NegotiationService.approve_for_club(
                    repo, club, str(offer["_id"]), "confirm", now=now
                )
                audit(
                    repo,
                    club["_id"],
                    "purchase",
                    {"offer_id": offer["_id"]},
                    "Compra confirmada sem ultrapassar caixa ou folha.",
                    now,
                )
        players = repo.many(
            "players",
            {
                "owner_club_id": club["_id"],
                "current_club_id": club["_id"],
                "status": {"$ne": "retired"},
            },
            limit=None,
        )
        lineup = repo.find("lineups", {"_id": club["_id"]})
        counts = {role: sum(p["position"] == role for p in players) for role in cls.TARGETS}
        for player in sorted(players, key=lambda p: p["strength"]):
            if (
                counts[player["position"]] > cls.TARGETS[player["position"]]
                and player["_id"] not in lineup["starters"]
                and player.get("status") == "available"
            ):
                if not repo.find(
                    "transfer_listings", {"player_id": player["_id"], "status": "active"}
                ):
                    kind = "loan" if player["age"] <= 23 else "sale"
                    price = round(
                        player.get("market_value", 50000) * (0.1 if kind == "loan" else 1.0)
                    )
                    MarketService.list_for_club(
                        repo,
                        club,
                        ListingInput(
                            player_id=str(player["_id"]),
                            type=kind,
                            price=max(1, price),
                            duration_days=5,
                        ),
                    )
                    audit(
                        repo,
                        club["_id"],
                        "listing",
                        {"player_id": player["_id"], "type": kind},
                        "Excedente por posição; empréstimo preserva jovens.",
                        now,
                    )
                break
        if repo.find(
            "transfer_offers",
            {
                "buyer_club_id": club["_id"],
                "negotiation_version": 2,
                "status": {"$in": ["pending", "counter_offer", "player_accepted"]},
                "expires_at": {"$gt": now},
            },
        ):
            return
        needs = [role for role, target in cls.TARGETS.items() if counts[role] < target]
        if not needs or len(players) >= 30:
            return
        role = min(needs, key=lambda r: counts[r] / cls.TARGETS[r])
        free = repo.many(
            "players",
            {
                "owner_club_id": None,
                "current_club_id": None,
                "position": role,
                "status": "available",
            },
            limit=None,
            sort=[("strength", -1), ("age", 1)],
        )
        for player in free:
            salary = SalaryService.reference(player)
            if not BotFinanceService.affordable(repo, club["_id"], 0, salary):
                continue
            ContractService.sign_for_club(repo, club, player, salary, 2, now=now)
            audit(
                repo,
                club["_id"],
                "free_agent",
                {"player_id": player["_id"], "salary": salary},
                "Carência por posição, sem taxa e com salário viável.",
                now,
            )
            return
        candidates = repo.many(
            "players",
            {
                "owner_club_id": {"$nin": [None, club["_id"]]},
                "position": role,
                "status": "available",
                "player_transfer_status": {"$in": ["listed", "available", "loan_listed"]},
            },
            limit=None,
            sort=[("strength", -1), ("age", 1)],
        )
        for player in candidates:
            kind = "loan" if player.get("player_transfer_status") == "loan_listed" else "sale"
            fee = MarketValueService.asking_price(player)
            salary = SalaryService.reference(player)
            if not BotFinanceService.affordable(repo, club["_id"], fee, salary):
                continue
            data = NegotiationInput(
                player_id=str(player["_id"]),
                offer_type=kind,
                transfer_value=fee,
                salary_offer=salary,
                contract_months=24,
                loan_months=6,
                salary_share=0.5,
            )
            NegotiationService.send_for_club(repo, club, data, now)
            audit(
                repo,
                club["_id"],
                "market_offer",
                {"player_id": player["_id"], "amount": fee, "type": kind},
                "Reposição de posição com preço e folha compatíveis.",
                now,
            )
            return


class BotManagerService:
    def __init__(self, repo):
        self.repo = repo

    @staticmethod
    def prepare(repo, club_id, now):
        club = repo.find("clubs", {"_id": club_id})
        if not club or not club.get("is_bot") or club.get("active") is False:
            return
        repo.update("clubs", {"_id": club_id}, {"$inc": {"roster_revision": 1}})
        lineup = BotLineupService.choose(repo, club, now)
        if lineup:
            BotTacticsService.choose(repo, club, lineup, now)

    def process_due(self, now=None):
        from app.services.competition import CompetitionService
        from app.services.physical_condition import PhysicalConditionService

        now = now or utcnow()
        season = CompetitionService.current(self.repo)
        if not season:
            return
        interval = timedelta(
            days=GameConfig.from_rules(self.repo.rules()).SEASON_DURATION_DAYS / 76
        )
        for bot in self.repo.many(
            "clubs",
            {
                "is_bot": True,
                "active": {"$ne": False},
                "$or": [
                    {"last_bot_management_at": {"$exists": False}},
                    {"last_bot_management_at": {"$lte": now - interval}},
                ],
            },
            limit=None,
        ):

            def operation(repo, identity=bot["_id"]):
                CompetitionService.lock(repo)
                club = repo.find("clubs", {"_id": identity})
                if (
                    not club
                    or not club.get("is_bot")
                    or club.get("active") is False
                    or club.get("last_bot_management_at", now - interval) > now - interval
                ):
                    return
                PhysicalConditionService().prepare(repo, identity, now)
                self.prepare(repo, identity, now)
                BotContractService.manage(repo, club, now)
                BotYouthService.manage(repo, club, now)
                BotTrainingService.manage(repo, club, now)
                try:
                    CompetitionService.require_transfer_window(repo, now)
                except HTTPException as exc:
                    if exc.status_code != 409:
                        raise
                else:
                    BotTransferService.manage(repo, club, now)
                BotStadiumService.manage(repo, club, now)
                self.prepare(repo, identity, now)
                repo.update("clubs", {"_id": identity}, {"$set": {"last_bot_management_at": now}})

            try:
                self.repo.transaction(operation)
            except HTTPException as exc:
                if exc.status_code != 409:
                    raise

                def blocked(repo, identity=bot["_id"], reason=exc.detail):
                    audit(repo, identity, "blocked", {}, reason, now)
                    repo.update(
                        "clubs", {"_id": identity}, {"$set": {"last_bot_management_at": now}}
                    )

                self.repo.transaction(blocked)
