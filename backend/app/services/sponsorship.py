"""Bounded monthly sponsorship offers and exclusive principal contracts."""

from datetime import timedelta

from bson import ObjectId
from fastapi import HTTPException

from app.config.economy import EconomyConfig
from app.config.game import GameConfig
from app.models.game import public, utcnow
from app.services.fan_base import FanBaseService


class SponsorshipService:
    @staticmethod
    def initial(repo, club_id, now=None):
        now = now or utcnow()
        if repo.find("sponsor_contracts", {"club_id": club_id}):
            return
        value = EconomyConfig.from_rules(repo.rules()).MONTHLY_SPONSORSHIP
        repo.insert(
            "sponsor_contracts",
            {
                "_id": ObjectId(),
                "club_id": club_id,
                "name": "Parceiro inicial",
                "status": "active",
                "monthly_value": value,
                "value": value,
                "duration_months": 12,
                "starts_at": now,
                "ends_at": now
                + timedelta(days=GameConfig.from_rules(repo.rules()).SEASON_DURATION_DAYS),
            },
        )

    @staticmethod
    def value(club):
        reputation = min(100, max(0, club.get("reputation", 10)))
        tier = min(4, max(0, club.get("division_tier", 0)))
        supporters = min(1, club.get("supporters", 1000) / 50000)
        recent = min(0.08, max(-0.05, club.get("result_streak", 0) * 0.01))
        factor = 0.95 + reputation * 0.003 + supporters * 0.1 - tier * 0.05 + recent
        confidence_factor = 0.5 + FanBaseService.confidence(club) / 100
        return round(500000 * max(0.7, min(1.5, factor)) * confidence_factor / 1000) * 1000

    @classmethod
    def offers(cls, repo, club, now=None):
        now = now or utcnow()
        existing = repo.many(
            "sponsor_offers",
            {"club_id": club["_id"], "status": "available", "expires_at": {"$gt": now}},
            limit=None,
        )
        if existing:
            return existing
        repo.update_many(
            "sponsor_offers",
            {"club_id": club["_id"], "status": "available"},
            {"$set": {"status": "expired"}},
        )
        base = cls.value(club)
        offers = []
        for name, months, factor, bonus in [
            ("Parceiro local", 6, 1, 0),
            ("Parceiro nacional", 12, 1.05, 10000),
        ]:
            offers.append(
                repo.insert(
                    "sponsor_offers",
                    {
                        "_id": ObjectId(),
                        "club_id": club["_id"],
                        "sponsor_name": name,
                        "name": name,
                        "monthly_value": round(base * factor),
                        "value": round(base * factor),
                        "duration_months": months,
                        "bonus": bonus,
                        "risk": 0,
                        "required_ranking": 0,
                        "duration_days": GameConfig.from_rules(repo.rules()).SEASON_DURATION_DAYS
                        * months
                        / 12,
                        "status": "available",
                        "created_at": now,
                        "expires_at": now
                        + timedelta(
                            days=GameConfig.from_rules(repo.rules()).SEASON_DURATION_DAYS / 12
                        ),
                    },
                )
            )
        return offers

    @classmethod
    def accept(cls, repo, club, identity, now=None):
        now = now or utcnow()
        repo.update("clubs", {"_id": club["_id"]}, {"$inc": {"sponsor_revision": 1}})
        repo.update_many(
            "sponsor_contracts",
            {"club_id": club["_id"], "status": "active", "ends_at": {"$lte": now}},
            {"$set": {"status": "expired"}},
        )
        if repo.find("sponsor_contracts", {"club_id": club["_id"], "status": "active"}):
            raise HTTPException(409, "Já existe patrocinador principal ativo.")
        if identity == "principal":
            offer = cls.offers(repo, club, now)[0]
        else:
            offer = repo.document("sponsor_offers", identity)
        if offer["club_id"] != club["_id"]:
            raise HTTPException(403, "Oferta de outro clube.")
        if offer["status"] != "available" or offer["expires_at"] <= now:
            raise HTTPException(409, "Oferta expirada ou encerrada.")
        contract = repo.insert(
            "sponsor_contracts",
            {
                "_id": ObjectId(),
                "club_id": club["_id"],
                "offer_id": offer["_id"],
                "name": offer["sponsor_name"],
                "monthly_value": offer["monthly_value"],
                "value": offer["monthly_value"],
                "duration_months": offer["duration_months"],
                "bonus": offer["bonus"],
                "status": "active",
                "starts_at": now,
                "ends_at": now
                + timedelta(
                    days=GameConfig.from_rules(repo.rules()).SEASON_DURATION_DAYS
                    * offer["duration_months"]
                    / 12
                ),
            },
        )
        repo.update_many(
            "sponsor_offers",
            {"club_id": club["_id"], "status": "available"},
            {"$set": {"status": "closed"}},
        )
        repo.update("sponsor_offers", {"_id": offer["_id"]}, {"$set": {"status": "accepted"}})
        if offer["bonus"]:
            repo.money(
                club["_id"], offer["bonus"], "sponsor_bonus", contract["_id"], effective_at=now
            )
        repo.event(club["_id"], "sponsor", "Novo patrocinador principal", now, contract["_id"])
        return public(contract)

    @classmethod
    def monthly_income(cls, repo, club_id, start, end):
        # Existing contracts retain the R$5k reference; negotiated replacements are prorated.
        contracts = repo.many(
            "sponsor_contracts",
            {"club_id": club_id, "starts_at": {"$lt": end}, "ends_at": {"$gt": start}},
            limit=None,
        )
        total = 0
        for contract in contracts:
            overlap = (
                min(end, contract["ends_at"]) - max(start, contract["starts_at"])
            ).total_seconds() / (end - start).total_seconds()
            total += round(
                contract.get(
                    "monthly_value", EconomyConfig.from_rules(repo.rules()).MONTHLY_SPONSORSHIP
                )
                * overlap
            )
        return total

    @classmethod
    def bot(cls, repo, club, now):
        if repo.find(
            "sponsor_contracts",
            {"club_id": club["_id"], "status": "active", "ends_at": {"$gt": now}},
        ):
            return
        offers = cls.offers(repo, club, now)
        best = max(
            offers,
            key=lambda offer: (
                (offer["monthly_value"] + offer["bonus"] / offer["duration_months"])
                * (1 - offer["risk"])
            ),
        )
        cls.accept(repo, club, str(best["_id"]), now)
