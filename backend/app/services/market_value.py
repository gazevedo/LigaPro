"""Nonlinear pricing independent of salary and professional potential."""

from math import ceil

from bson import ObjectId

from app.config.market_value import MarketValueConfig
from app.models.game import utcnow
from app.services.salary import interpolate


class MarketValueService:
    def __init__(self, config=None):
        self.config = config or MarketValueConfig()

    def calculate(self, player, *, club=None, contract=None, rating=6, now=None):
        c = self.config
        strength = player.get("strength", player.get("overall", 50))
        age = next(factor for ceiling, factor in c.age_factors if player["age"] <= ceiling)
        stars = c.stars_factors[max(0, min(5, player.get("stars", 0)))]
        performance = max(0.90, min(1.15, 1 + (rating - 6) * 0.04))
        club = club or {}
        reputation = max(0.95, min(1.10, 0.95 + club.get("reputation", 10) * 0.0015))
        months = (
            (contract["expires_at"] - (now or utcnow())).total_seconds()
            / contract["salary_period_seconds"]
            if contract
            else 0
        )
        months = ceil(max(0, months))
        contract_factor = (
            1.10
            if months >= 24
            else 1.05
            if months > 12
            else 1
            if months > 6
            else 0.90
            if months > 3
            else 0.75
        )
        # A free player retains an estimated market value; the actual transfer fee is zero.
        if not contract:
            contract_factor = 1
        value = (
            interpolate(strength, c.strength_curve)
            * 100
            * age
            * stars
            * dict(c.position_factors).get(player["position"], 1)
            * performance
            * contract_factor
            * c.division_factors[min(4, max(0, club.get("division_tier", 0)))]
            * reputation
        )
        return max(c.minimum, min(c.maximum, round(value / 10000) * 10000))

    @staticmethod
    def asking_price(player, status=None):
        if player.get("owner_club_id") is None:
            return 0
        status = status or player.get("player_transfer_status", "not_for_sale")
        factor = {"listed": 1.0, "loan_listed": 0.10, "available": 1.15, "not_for_sale": 1.75}.get(
            status, 1.15
        )
        return (
            round(player.get("market_value", player.get("value", 50000)) * factor / 10000) * 10000
        )

    def recalculate(self, repo, players, reason, reference=None, now=None, collection="players"):
        now = now or utcnow()
        players = list(players)
        if not players:
            return
        ids = [p["_id"] for p in players]
        clubs = {
            c["_id"]: c
            for c in repo.many(
                "clubs",
                {"_id": {"$in": list({p.get("owner_club_id") for p in players})}},
                limit=None,
            )
        }
        contracts = {
            c["player_id"]: c
            for c in repo.many(
                "player_contracts",
                {"player_id": {"$in": ids}, "status": {"$in": ["active", "expiring"]}},
                limit=None,
            )
        }
        ratings = list(
            repo.database.player_match_ratings.aggregate(
                [
                    {"$match": {"player_id": {"$in": ids}}},
                    {"$sort": {"match_date": -1, "_id": -1}},
                    {
                        "$group": {
                            "_id": "$player_id",
                            "ratings": {"$firstN": {"input": "$rating", "n": 5}},
                        }
                    },
                ],
                session=repo.session,
            )
        )
        averages = {r["_id"]: sum(r["ratings"][:5]) / len(r["ratings"][:5]) for r in ratings}
        for player in players:
            value = self.calculate(
                player,
                club=clubs.get(player.get("owner_club_id")),
                contract=contracts.get(player["_id"]),
                rating=averages.get(player["_id"], 6),
                now=now,
            )
            if value == player.get("market_value") and reason not in {"promotion", "transfer"}:
                continue
            repo.update(
                collection,
                {"_id": player["_id"]},
                {
                    "$set": {
                        "market_value": value,
                        "value": value,
                        "asking_price": self.asking_price({**player, "market_value": value}),
                        "transfer_fee": 0 if player.get("owner_club_id") is None else value,
                    }
                },
            )
            repo.insert(
                "player_market_value_history",
                {
                    "_id": ObjectId(),
                    "player_id": player["_id"],
                    "value": value,
                    "reason": reason,
                    "reference_id": reference,
                    "created_at": now,
                },
            )
