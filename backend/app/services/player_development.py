from random import Random

from bson import ObjectId
from fastapi import HTTPException

from app.config.game import GameConfig
from app.config.team_performance import ChemistryConfig, MoraleConfig
from app.models.game import utcnow
from app.models.player import market_value, player_public
from app.services.chemistry import ChemistryService
from app.services.player_contracts import ContractService


class PlayerGeneratorService:
    def __init__(self, config=None, seed=None):
        self.config = config or GameConfig()
        self.rng = Random(seed)

    def player(self, club_id, country_id, position=None, youth=False):
        strength = min(
            self.config.MAX_PLAYER_LEVEL,
            self.rng.randint(25, 45) if youth else self.rng.randint(40, 60),
        )
        first = self.rng.choice(("João", "Pedro", "Lucas", "André", "Rafael", "Bruno", "Caio"))
        last = self.rng.choice(("Silva", "Santos", "Costa", "Souza", "Lima", "Alves", "Oliveira"))
        age = self.rng.randint(14, 17) if youth else self.rng.randint(18, 30)
        potential = self.potential(strength, youth)
        value = market_value(strength, potential, age)
        return {
            "_id": ObjectId(),
            "name": f"{first} {last}",
            "position": position or self.rng.choice(("GK", "DEF", "MID", "ATT")),
            "age": age,
            "potential": potential,
            "morale": MoraleConfig().initial,
            "integration": ChemistryConfig().initial,
            "joined_at": utcnow(),
            "strength": strength,
            "overall": strength,
            "training_level": 0,
            "disease": None,
            "status": "active",
            "value": value,
            "market_value": value,
            "country_id": country_id,
            "owner_club_id": club_id,
            "current_club_id": club_id,
            "created_at": utcnow(),
        }

    def potential(self, strength, youth=False):
        ceiling = max(strength, self.config.MAX_PLAYER_LEVEL)
        promising = youth and self.rng.random() < 0.75
        low = max(strength, min(55, ceiling)) if promising else max(1, strength)
        high = ceiling if promising else min(ceiling, max(1, strength) + (30 if not youth else 15))
        return self.rng.randint(low, high)

    def squad(self, club_id, country_id):
        return [
            self.player(club_id, country_id, position)
            for position, count in self.config.INITIAL_POSITION_COUNTS
            for _ in range(count)
        ]

    def youth(self, club_id, country_id):
        return [
            self.player(club_id, country_id, youth=True)
            for _ in range(self.config.YOUTH_PLAYERS_PER_SEASON)
        ]


class TrainingService:
    def __init__(self, repository):
        self.repo = repository

    def get(self, user, youth=False):
        club = self.repo.owned(user.id)
        collection = "youth_players" if youth else "players"
        return [
            player_public(player)
            for player in self.repo.many(
                collection,
                {"current_club_id": club["_id"], "status": {"$nin": ["retired", "promoted"]}},
                limit=None,
            )
        ]

    def train(self, user, identity):
        def operation(repo):
            club = repo.owned(user.id)
            config = GameConfig.from_rules(repo.rules())
            if not ObjectId.is_valid(identity):
                raise HTTPException(404, "Jogador não encontrado.")
            for collection in ("players", "youth_players"):
                player = repo.find(collection, {"_id": ObjectId(identity)})
                if player:
                    break
            else:
                raise HTTPException(404, "Jogador não encontrado.")
            if player["current_club_id"] != club["_id"]:
                raise HTTPException(403, "Jogador de outro clube.")
            if player.get("status") == "retired":
                raise HTTPException(409, "Jogador aposentado.")
            strength = player.get("strength", player.get("overall", 50))
            if strength >= min(
                config.MAX_PLAYER_LEVEL, player.get("potential", config.MAX_PLAYER_LEVEL)
            ):
                raise HTTPException(409, "Jogador atingiu o limite de desenvolvimento.")
            level = player.get("training_level", 0) + 1
            if level >= 100:
                strength, level = strength + 1, 0
            value = market_value(
                strength, player.get("potential", config.MAX_PLAYER_LEVEL), player["age"]
            )
            return player_public(
                repo.update(
                    collection,
                    {"_id": player["_id"]},
                    {
                        "$set": {
                            "training_level": level,
                            "strength": strength,
                            "overall": strength,
                            "value": value,
                            "market_value": value,
                        }
                    },
                )
            )

        return self.repo.transaction(operation)

    def promote(self, user, identity):
        def operation(repo):
            club = repo.owned(user.id)
            player = repo.document("youth_players", identity)
            if player["current_club_id"] != club["_id"]:
                raise HTTPException(403, "Jogador de outro clube.")
            if player.get("status") != "active":
                raise HTTPException(409, "Jogador indisponível.")
            if player["age"] < GameConfig.from_rules(repo.rules()).YOUTH_PROMOTION_AGE:
                raise HTTPException(409, "Jogador ainda não tem idade para promoção.")
            repo.update("clubs", {"_id": club["_id"]}, {"$inc": {"roster_revision": 1}})
            professional = {
                **player,
                "promoted_at": utcnow(),
                "morale": min(100, player.get("morale", 50) + MoraleConfig().promotion),
                "integration": 0,
                "joined_at": utcnow(),
            }
            ChemistryService().recruit(repo, club["_id"])
            repo.insert("players", professional)
            ContractService.initial(repo, [professional])
            repo.update(
                "youth_players",
                {"_id": player["_id"]},
                {"$set": {"status": "promoted", "promoted_at": professional["promoted_at"]}},
            )
            repo.update("lineups", {"_id": club["_id"]}, {"$addToSet": {"reserves": player["_id"]}})
            return player_public(professional)

        return self.repo.transaction(operation)


class PlayerAgingService:
    @staticmethod
    def probability(age, values):
        return next(
            (probability for threshold, probability in reversed(values) if age >= threshold), 0
        )

    def process(self, repo, season_id, config):
        rng = Random(str(season_id))
        affected_clubs = set()
        for collection in ("players", "youth_players"):
            for player in repo.many(
                collection,
                {"status": {"$nin": ["retired", "promoted"]}},
                limit=None,
                sort=[("_id", 1)],
            ):
                age = player["age"] + 1
                values = {"age": age}
                if age >= config.PLAYER_DECLINE_AGE:
                    if rng.random() < self.probability(age, config.DECLINE_PROBABILITIES):
                        strength = max(0, player.get("strength", player.get("overall", 50)) - 1)
                        values.update(strength=strength, overall=strength)
                    if rng.random() < self.probability(age, config.RETIREMENT_PROBABILITIES):
                        values.update(
                            status="retired", retired_at=utcnow(), retired_season_id=season_id
                        )
                strength = values.get("strength", player.get("strength", player.get("overall", 50)))
                value = market_value(
                    strength, player.get("potential", config.MAX_PLAYER_LEVEL), age
                )
                values.update(value=value, market_value=value)
                repo.update(collection, {"_id": player["_id"]}, {"$set": values})
                if values.get("status") == "retired" and collection == "players":
                    ContractService.terminate(repo, player["_id"], reason="retired")
                    if player["current_club_id"] is not None:
                        affected_clubs.add(player["current_club_id"])
                    repo.update_many(
                        "lineups",
                        {"_id": player["current_club_id"]},
                        {"$pull": {"starters": player["_id"], "reserves": player["_id"]}},
                    )
                    repo.update_many(
                        "transfer_listings",
                        {"player_id": player["_id"], "status": "active"},
                        {"$set": {"status": "closed"}},
                    )
                    listings = repo.many(
                        "transfer_listings", {"player_id": player["_id"]}, limit=None
                    )
                    repo.update_many(
                        "transfer_offers",
                        {
                            "listing_id": {"$in": [listing["_id"] for listing in listings]},
                            "status": "pending",
                        },
                        {"$set": {"status": "closed"}},
                    )
                    repo.update_many(
                        "player_loans",
                        {"player_id": player["_id"], "status": "active"},
                        {"$set": {"status": "retired"}},
                    )

        # Replace retired starters with actual reserves where the remaining squad
        # supports a legal formation. An insufficient squad can still finish the
        # season; the match runner records a walkover rather than invent players.
        from app.services.game import MarketService

        for club_id in affected_clubs:
            try:
                MarketService.repair_lineup(repo, club_id)
            except HTTPException as exc:
                if exc.status_code != 409:
                    raise


def bootstrap_player_attributes(repo):
    config = GameConfig.from_rules(repo.rules())
    for collection in ("players", "youth_players"):
        for player in repo.many(
            collection,
            {
                "$or": [
                    {"potential": {"$exists": False}},
                    {"morale": {"$exists": False}},
                    {"integration": {"$exists": False}},
                ]
            },
            limit=None,
        ):
            strength = player.get("strength", player.get("overall", 50))
            potential = player.get(
                "potential",
                PlayerGeneratorService(config, str(player["_id"])).potential(
                    strength, collection == "youth_players"
                ),
            )
            value = market_value(strength, potential, player["age"])
            repo.update(
                collection,
                {"_id": player["_id"]},
                {
                    "$set": {
                        "potential": potential,
                        "morale": player.get("morale", 50),
                        "integration": player.get("integration", 40),
                        "joined_at": player.get("joined_at", player.get("created_at", utcnow())),
                        "value": value,
                        "market_value": value,
                    }
                },
            )
    chemistry = ChemistryService()
    for club in repo.many("clubs", {}, limit=None):
        if not repo.find("club_chemistry", {"_id": club["_id"]}):
            chemistry.save(repo, club["_id"], {})
