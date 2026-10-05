"""Explicit seller, player and buyer approvals; settlement reuses the market ledger."""

from datetime import timedelta

from bson import ObjectId
from fastapi import HTTPException

from app.config.game import GameConfig
from app.models.game import public, utcnow
from app.services.market_value import MarketValueService
from app.services.salary import SalaryService


class PlayerContractDecisionService:
    @staticmethod
    def evaluate(player, buyer, salary, months, expected_starter=True, seller=None):
        reference = SalaryService.reference(player)
        if salary < round(reference * 0.75):
            return {"accepted": False, "reason": "Salário abaixo da expectativa do jogador."}
        if not 1 <= months <= 60:
            return {"accepted": False, "reason": "Duração de contrato inválida."}
        if (
            player.get("strength", 50) >= 80
            and buyer.get("division_tier", 0) > ((seller or {}).get("division_tier", 0) + 2)
            and buyer.get("reputation", 10) < 50
        ):
            return {
                "accepted": False,
                "reason": "Divisão e reputação abaixo da expectativa do jogador.",
            }
        if player.get("stars", 0) >= 3 and not expected_starter and salary < reference * 1.15:
            return {
                "accepted": False,
                "reason": "O jogador espera titularidade ou compensação salarial.",
            }
        if player.get("stars", 0) >= 3 and months < 12:
            return {"accepted": False, "reason": "O jogador procura um contrato mais longo."}
        return {"accepted": True, "reason": "Contrato aceito pelo jogador."}


class NegotiationService:
    def __init__(self, repo):
        self.repo = repo

    @staticmethod
    def send_for_club(repo, club, data, now=None):
        from app.services.player_contracts import ContractService

        now = now or utcnow()
        player = repo.document("players", data.player_id)
        seller_id = player.get("owner_club_id")
        if (
            seller_id is None
            or seller_id == club["_id"]
            or player.get("status") == "retired"
            or player.get("current_club_id") != seller_id
        ):
            raise HTTPException(409, "Jogador indisponível para esta negociação.")
        # Serialize offers and listings against transfer/loan/contract changes.
        repo.update("players", {"_id": player["_id"]}, {"$inc": {"market_revision": 1}})
        if repo.find(
            "transfer_offers",
            {
                "player_id": player["_id"],
                "buyer_club_id": club["_id"],
                "status": {"$in": ["pending", "counter_offer", "player_accepted"]},
            },
        ):
            raise HTTPException(409, "Já existe negociação aberta para este jogador.")
        if repo.find("club_finances", {"_id": club["_id"]})["balance"] < data.transfer_value:
            raise HTTPException(409, "Saldo insuficiente.")
        current = ContractService.current(repo, player["_id"])
        if not current or current["expires_at"] <= now:
            raise HTTPException(409, "Jogador sem contrato vigente.")
        if (
            data.offer_type == "loan"
            and now + timedelta(seconds=current["salary_period_seconds"] * data.loan_months)
            > current["expires_at"]
        ):
            raise HTTPException(409, "Empréstimo ultrapassa o contrato vigente.")
        ContractService.capacity(
            repo,
            club["_id"],
            data.salary_offer
            if data.offer_type == "sale"
            else round(current["salary"] * data.salary_share),
        )
        listing = repo.find("transfer_listings", {"player_id": player["_id"], "status": "active"})
        if listing and listing["type"] != data.offer_type:
            raise HTTPException(409, "Tipo de negociação incompatível com o anúncio.")
        if not listing:
            listing = repo.insert(
                "transfer_listings",
                {
                    "_id": ObjectId(),
                    "player_id": player["_id"],
                    "seller_club_id": seller_id,
                    "type": data.offer_type,
                    "price": MarketValueService.asking_price(player),
                    "duration_days": data.loan_months
                    * GameConfig.from_rules(repo.rules()).SEASON_DURATION_DAYS
                    / 12,
                    "status": "active",
                    "negotiation_only": True,
                    "created_at": now,
                },
            )
        offer = repo.insert(
            "transfer_offers",
            {
                "_id": ObjectId(),
                "listing_id": listing["_id"],
                "seller_club_id": seller_id,
                "buyer_club_id": club["_id"],
                **data.model_dump(exclude={"player_id"}),
                "player_id": player["_id"],
                "salary_offer": current["salary"]
                if data.offer_type == "loan"
                else data.salary_offer,
                "amount": data.transfer_value,
                "status": "pending",
                "negotiation_version": 2,
                "created_at": now,
                "expires_at": now
                + timedelta(days=GameConfig.from_rules(repo.rules()).SEASON_DURATION_DAYS / 12),
            },
        )
        return public(offer)

    def send(self, user, data):
        return self.repo.transaction(
            lambda repo: self.send_for_club(repo, repo.owned(user.id), data)
        )

    @staticmethod
    def approve_for_club(repo, club, identity, action, data=None, now=None):
        now = now or utcnow()
        offer = repo.document("transfer_offers", identity)
        if offer.get("negotiation_version") != 2:
            from math import ceil

            from app.services.player_contracts import ContractService

            listing = repo.document("transfer_listings", str(offer["listing_id"]))
            player = repo.document("players", str(listing["player_id"]))
            contract = ContractService.current(repo, player["_id"])
            if not contract or offer["status"] != "pending":
                raise HTTPException(409, "Negociação anterior encerrada.")
            offer = repo.update(
                "transfer_offers",
                {"_id": offer["_id"]},
                {
                    "$set": {
                        "negotiation_version": 2,
                        "player_id": player["_id"],
                        "offer_type": listing["type"],
                        "transfer_value": offer["amount"],
                        "salary_offer": contract["salary"],
                        "contract_months": max(
                            1,
                            min(
                                60,
                                ceil(
                                    (contract["expires_at"] - now).total_seconds()
                                    / contract["salary_period_seconds"]
                                ),
                            ),
                        ),
                        "loan_months": max(
                            1,
                            min(
                                12,
                                ceil(
                                    listing["duration_days"]
                                    * 12
                                    / GameConfig.from_rules(repo.rules()).SEASON_DURATION_DAYS
                                ),
                            ),
                        ),
                        "salary_share": 0,
                        "keep_existing_contract": True,
                        "expires_at": now
                        + timedelta(
                            days=GameConfig.from_rules(repo.rules()).SEASON_DURATION_DAYS / 12
                        ),
                    }
                },
            )
        allowed = {"pending", "counter_offer", "player_accepted"}
        if offer["status"] not in allowed or offer["expires_at"] <= now:
            raise HTTPException(409, "Negociação encerrada ou expirada.")
        if action in {"accept", "reject", "counter"} and offer["seller_club_id"] != club["_id"]:
            raise HTTPException(403, "Proposta de outro clube.")
        if action in {"confirm", "accept_counter"} and offer["buyer_club_id"] != club["_id"]:
            raise HTTPException(403, "Proposta de outro clube.")
        repo.update("transfer_offers", {"_id": offer["_id"]}, {"$inc": {"revision": 1}})
        if action == "reject":
            return public(
                repo.update(
                    "transfer_offers",
                    {"_id": offer["_id"]},
                    {"$set": {"status": "rejected", "rejected_at": now}},
                )
            )
        if action == "counter":
            if offer["status"] == "player_accepted":
                raise HTTPException(409, "Contrato já aceito pelo jogador.")
            changes = data.model_dump(exclude_none=True)
            if offer["offer_type"] == "loan" and "salary_offer" in changes:
                from app.services.player_contracts import ContractService

                contract = ContractService.current(repo, offer["player_id"])
                if not contract or changes["salary_offer"] != contract["salary"]:
                    raise HTTPException(
                        422, "Empréstimo mantém o salário contratado; negocie a participação."
                    )
            changes["status"] = "counter_offer"
            if "transfer_value" in changes:
                changes["amount"] = changes["transfer_value"]
            return public(repo.update("transfer_offers", {"_id": offer["_id"]}, {"$set": changes}))
        if action in {"accept", "accept_counter"}:
            if action == "accept_counter" and offer["status"] != "counter_offer":
                raise HTTPException(409, "Não há contraproposta para aceitar.")
            if action == "accept" and offer["status"] != "pending":
                raise HTTPException(409, "Aguarde o comprador responder à contraproposta.")
            player = repo.document("players", str(offer["player_id"]))
            buyer = repo.find("clubs", {"_id": offer["buyer_club_id"]})
            seller = repo.find("clubs", {"_id": offer["seller_club_id"]})
            decision = PlayerContractDecisionService.evaluate(
                player,
                buyer,
                offer["salary_offer"],
                offer["loan_months"] if offer["offer_type"] == "loan" else offer["contract_months"],
                offer.get("expected_starter", True),
                seller,
            )
            return public(
                repo.update(
                    "transfer_offers",
                    {"_id": offer["_id"]},
                    {
                        "$set": {
                            "status": "player_accepted"
                            if decision["accepted"]
                            else "player_rejected",
                            "player_decision": decision,
                            "seller_accepted_at": now,
                        }
                    },
                )
            )
        if action == "confirm":
            if offer["status"] != "player_accepted":
                raise HTTPException(409, "Vendedor e jogador devem aceitar antes da confirmação.")
            from app.services.game import MarketService

            seller = repo.find("clubs", {"_id": offer["seller_club_id"]})
            player = repo.document("players", str(offer["player_id"]))
            decision = PlayerContractDecisionService.evaluate(
                player,
                club,
                offer["salary_offer"],
                offer["loan_months"] if offer["offer_type"] == "loan" else offer["contract_months"],
                offer.get("expected_starter", True),
                seller,
            )
            if not decision["accepted"]:
                raise HTTPException(409, decision["reason"])
            return MarketService.complete_for_club(repo, seller, identity, now=now, terms=offer)
        raise HTTPException(422, "Ação inválida.")

    def act(self, user, identity, action, data=None):
        return self.repo.transaction(
            lambda repo: self.approve_for_club(repo, repo.owned(user.id), identity, action, data)
        )

    @staticmethod
    def expire(repo, now):
        repo.update_many(
            "transfer_offers",
            {
                "negotiation_version": 2,
                "status": {"$in": ["pending", "counter_offer", "player_accepted"]},
                "expires_at": {"$lte": now},
            },
            {"$set": {"status": "expired"}},
        )
        repo.update_many(
            "transfer_listings",
            {
                "negotiation_only": True,
                "status": "active",
                "created_at": {
                    "$lte": now
                    - timedelta(days=GameConfig.from_rules(repo.rules()).SEASON_DURATION_DAYS / 12)
                },
            },
            {"$set": {"status": "closed"}},
        )
