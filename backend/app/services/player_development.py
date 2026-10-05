from random import Random

from bson import ObjectId
from fastapi import HTTPException

from app.config.game import GameConfig
from app.config.team_performance import ChemistryConfig, MoraleConfig
from app.models.game import utcnow
from app.models.player import FORBIDDEN, SKILLS, market_value, normalize_player, player_public
from app.services.chemistry import ChemistryService
from app.services.market_value import MarketValueService
from app.services.player_contracts import ContractService
from app.services.salary import SalaryService


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
        document = {
            "_id": ObjectId(),
            "name": f"{first} {last}",
            "position": position or self.rng.choice(("GK", "FB", "CB", "MID", "ATT")),
            "age": age,
            "potential": potential,
            "morale": MoraleConfig().initial,
            "integration": ChemistryConfig().initial,
            "joined_at": utcnow(),
            "model_version": 22,
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
        document.update(normalize_player(document))
        document["innate_characteristics"] = self.rng.sample(
            ["reflexes", "positioning", "penalty_saving"]
            if document["position"] == "GK"
            else [
                "passing",
                "playmaking",
                "heading",
                "crossing",
                "tackling",
                "dribbling",
                "finishing",
                "marking",
                "stamina",
                "speed",
            ],
            2,
        )
        document["preferred_side"] = self.rng.choice(("left", "right", "both"))
        document["stars"] = 0
        document["salary_reference"] = SalaryService.reference(document)
        for key in FORBIDDEN - ({"potential", "estimated_potential_capacity"} if youth else set()):
            document.pop(key, None)
        if youth:
            document.update(club_id=club_id, estimated_potential_capacity=potential)
        return document

    def potential(self, strength, youth=False):
        ceiling = max(strength, self.config.MAX_PLAYER_LEVEL)
        promising = youth and self.rng.random() < 0.75
        low = max(strength, min(55, ceiling)) if promising else max(1, strength)
        high = ceiling if promising else min(ceiling, max(1, strength) + (30 if not youth else 15))
        return self.rng.randint(low, high)

    def squad(self, club_id, country_id):
        players = []
        for position, count in self.config.INITIAL_POSITION_COUNTS:
            for index in range(count):
                role = (
                    "FB"
                    if position == "DEF" and index < count // 2
                    else "CB"
                    if position == "DEF"
                    else position
                )
                players.append(self.player(club_id, country_id, role))
        return players

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
        from app.services.physical_condition import PhysicalConditionService

        if not youth:
            self.repo.transaction(
                lambda repo: PhysicalConditionService().prepare(repo, club["_id"], utcnow())
            )
        players = self.repo.many(
            collection,
            {"current_club_id": club["_id"], "status": {"$nin": ["retired", "promoted"]}},
            limit=None,
        )
        progress = {
            row["_id"]: row.get("progress", 0)
            for row in self.repo.many(
                "player_training", {"_id": {"$in": [p["_id"] for p in players]}}, limit=None
            )
        }
        return [
            {
                **player_public(player, youth=youth),
                "training_progress": progress.get(player["_id"], 0),
            }
            for player in players
        ]

    def train(self, user, identity, skill=None):
        def operation(repo):
            from app.services.physical_condition import PhysicalConditionService

            club = repo.owned(user.id)
            PhysicalConditionService().prepare(repo, club["_id"], utcnow())
            return self.train_for_club(repo, club, identity, skill)

        return self.repo.transaction(operation)

    @staticmethod
    def train_for_club(repo, club, identity, skill=None):
        if not ObjectId.is_valid(identity):
            raise HTTPException(404, "Jogador não encontrado.")
        collection = "players"
        player = repo.find(collection, {"_id": ObjectId(identity)})
        if not player:
            collection = "youth_players"
            player = repo.find(collection, {"_id": ObjectId(identity)})
        if not player:
            raise HTTPException(404, "Jogador não encontrado.")
        if player["current_club_id"] != club["_id"]:
            raise HTTPException(403, "Jogador de outro clube.")
        if player.get("status") in {"retired", "injured", "suspended"}:
            raise HTTPException(409, "Jogador indisponível para treino normal.")
        skills = normalize_player(player)["individual_skills"]
        skill = skill or {
            "GK": "goalkeeping",
            "CB": "tackling",
            "FB": "speed",
            "DEF": "tackling",
            "MID": "playmaking",
            "ATT": "finishing",
        }.get(player["position"], "passing")
        if skill not in SKILLS:
            raise HTTPException(422, "Habilidade inválida.")
        ceiling = (
            player.get("estimated_potential_capacity", player.get("potential", 100))
            if collection == "youth_players"
            else 100
        )
        if skills[skill] >= ceiling:
            raise HTTPException(409, "Jogador atingiu o limite de desenvolvimento.")
        progress = repo.find("player_training", {"_id": player["_id"]}) or {"progress": 0}
        stadium = repo.find("stadiums", {"_id": club["_id"]}) or {}
        training_level = stadium.get("facilities", {}).get("training", 1)
        level = progress["progress"] + 1 + min(2, max(0, training_level - 1))
        changes = {}
        if level >= 100:
            level -= 100
            skills[skill] += 1
            strength = min(ceiling, max(1, round(sum(skills.values()) / len(skills))))
            changes.update(individual_skills=skills, strength=strength, overall=strength)
        repo.database.player_training.update_one(
            {"_id": player["_id"]},
            {
                "$set": {
                    "player_id": player["_id"],
                    "progress": level,
                    "last_skill": skill,
                    "updated_at": utcnow(),
                },
                "$inc": {"season_sessions": 1},
            },
            upsert=True,
            session=repo.session,
        )
        if changes:
            updated = repo.update(collection, {"_id": player["_id"]}, {"$set": changes})
            repo.update(
                collection,
                {"_id": player["_id"]},
                {"$set": {"salary_reference": SalaryService.reference(updated)}},
            )
            MarketValueService().recalculate(repo, [updated], "training", collection=collection)
        return {
            **player_public(
                repo.find(collection, {"_id": player["_id"]}), youth=collection == "youth_players"
            ),
            "training_progress": level,
        }

    def release(self, user, identity):
        def operation(repo):
            club = repo.owned(user.id)
            player = repo.document("youth_players", identity)
            if player["current_club_id"] != club["_id"]:
                raise HTTPException(403, "Jogador de outro clube.")
            if player.get("status") not in {"available", "active"}:
                raise HTTPException(409, "Júnior indisponível.")
            repo.update("clubs", {"_id": club["_id"]}, {"$inc": {"roster_revision": 1}})
            repo.update(
                "youth_players",
                {"_id": player["_id"]},
                {
                    "$set": {
                        "status": "released",
                        "owner_club_id": None,
                        "current_club_id": None,
                        "released_at": utcnow(),
                    }
                },
            )
            repo.event(club["_id"], "youth", "Júnior dispensado", reference=player["_id"])
            return {"status": "released"}

        return self.repo.transaction(operation)

    def promote(self, user, identity):
        return self.repo.transaction(
            lambda repo: self.promote_for_club(repo, repo.owned(user.id), identity)
        )

    @staticmethod
    def promote_for_club(repo, club, identity):
        player = repo.document("youth_players", identity)
        if player["current_club_id"] != club["_id"]:
            raise HTTPException(403, "Jogador de outro clube.")
        if player.get("status") not in {"active", "available"}:
            raise HTTPException(409, "Jogador indisponível.")
        if player["age"] < GameConfig.from_rules(repo.rules()).YOUTH_PROMOTION_AGE:
            raise HTTPException(409, "Jogador ainda não tem idade para promoção.")
        repo.update("clubs", {"_id": club["_id"]}, {"$inc": {"roster_revision": 1}})
        professional = {
            **player,
            "promoted_at": utcnow(),
            "morale": min(100, player.get("morale", 50) + MoraleConfig().promotion),
            "joined_at": utcnow(),
            "model_version": 22,
        }
        for key in FORBIDDEN:
            professional.pop(key, None)
        ChemistryService().recruit(repo, club["_id"])
        ContractService.capacity(repo, club["_id"], SalaryService.reference(professional))
        repo.insert("players", professional)
        ContractService.initial(repo, [professional])
        repo.update(
            "youth_players",
            {"_id": player["_id"]},
            {"$set": {"status": "promoted", "promoted_at": professional["promoted_at"]}},
        )
        repo.update("lineups", {"_id": club["_id"]}, {"$addToSet": {"reserves": player["_id"]}})
        MarketValueService().recalculate(repo, [professional], "promotion")
        return player_public(repo.find("players", {"_id": player["_id"]}))


class PlayerAgingService:
    @staticmethod
    def probability(age, values):
        return next(
            (probability for threshold, probability in reversed(values) if age >= threshold), 0
        )

    def process(self, repo, season_id, config):
        rng = Random(str(season_id))
        affected_clubs = set()
        stats = {
            row["player_id"]: row
            for row in repo.many("player_season_stats", {"season_id": season_id}, limit=None)
        }
        training = {
            row["_id"]: row.get("season_sessions", 0)
            for row in repo.many("player_training", {}, limit=None)
        }
        from datetime import timedelta

        from app.services.career_development import CareerDevelopmentService

        season = repo.find("seasons", {"_id": season_id}) or {}
        injuries = {}
        for item in repo.many(
            "player_injuries",
            {"started_at": {"$gte": season.get("starts_at", utcnow() - timedelta(days=30))}},
            limit=None,
        ):
            injuries[item["player_id"]] = (
                injuries.get(item["player_id"], 0)
                + (item["expected_return_at"] - item["started_at"]).total_seconds() / 86400
            )

        for collection in ("players", "youth_players"):
            for player in repo.many(
                collection,
                {"status": {"$nin": ["retired", "promoted"]}},
                limit=None,
                sort=[("_id", 1)],
            ):
                values, reason = CareerDevelopmentService.evolve(
                    player,
                    rng,
                    stats.get(player["_id"], {}).get("minutes", 0),
                    training.get(player["_id"], 0),
                    injuries.get(player["_id"], 0),
                    player.get("estimated_potential_capacity", player.get("potential", 100))
                    if collection == "youth_players"
                    else 100,
                )
                age = values["age"]
                if age >= config.PLAYER_DECLINE_AGE:
                    # Keep configured overrides used by managed universes/tests.
                    if rng.random() < self.probability(age, config.DECLINE_PROBABILITIES):
                        values.update(
                            strength=max(1, player["strength"] - 1),
                            overall=max(1, player["strength"] - 1),
                            individual_skills={
                                key: max(0, value - 1)
                                for key, value in normalize_player(player)[
                                    "individual_skills"
                                ].items()
                            },
                        )
                        reason = "regression"
                    if values["retired"] or rng.random() < self.probability(
                        age, config.RETIREMENT_PROBABILITIES
                    ):
                        values.update(
                            status="retired",
                            retired=True,
                            retired_at=season.get("ends_at", utcnow()),
                            retired_season_id=season_id,
                        )
                        reason = "retirement"
                repo.insert(
                    "player_development_history",
                    {
                        "_id": ObjectId(),
                        "player_id": player["_id"],
                        "old_strength": player["strength"],
                        "new_strength": values["strength"],
                        "reason": reason,
                        "season_id": season_id,
                        "created_at": season.get("ends_at", utcnow()),
                    },
                )
                updated = repo.update(collection, {"_id": player["_id"]}, {"$set": values})
                repo.update(
                    collection,
                    {"_id": player["_id"]},
                    {"$set": {"salary_reference": SalaryService.reference(updated)}},
                )
                MarketValueService().recalculate(
                    repo, [updated], "aging", season_id, collection=collection
                )
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

        repo.update_many("player_training", {}, {"$set": {"season_sessions": 0}})
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
    for collection in ("players", "youth_players"):
        for player in repo.many(collection, {"model_version": {"$ne": 22}}, limit=None):

            def operation(tx, document=player, target=collection):
                values = normalize_player(document)
                values.update(
                    model_version=22,
                    joined_at=document.get("joined_at", document.get("created_at", utcnow())),
                    updated_at=utcnow(),
                    salary_reference=SalaryService.reference({**document, **values}),
                )
                contract = (
                    ContractService.current(tx, document["_id"]) if target == "players" else None
                )
                if contract:
                    values.update(
                        salary=contract["salary"],
                        contract_status=contract["status"],
                        contract_expires_at=contract["expires_at"],
                    )
                elif target == "players":
                    values.update(salary=0, contract_status="expired", contract_expires_at=None)
                if document.get("training_level"):
                    tx.database.player_training.update_one(
                        {"_id": document["_id"]},
                        {
                            "$setOnInsert": {
                                "player_id": document["_id"],
                                "progress": document["training_level"],
                            }
                        },
                        upsert=True,
                        session=tx.session,
                    )
                removed = FORBIDDEN - (
                    {"potential", "estimated_potential_capacity"}
                    if target == "youth_players"
                    else set()
                )
                tx.update(
                    target,
                    {"_id": document["_id"]},
                    {"$set": values, "$unset": {key: "" for key in removed}},
                )
                MarketValueService().recalculate(
                    tx,
                    [tx.find(target, {"_id": document["_id"]})],
                    "model_migration",
                    collection=target,
                )

            repo.transaction(operation)
    chemistry = ChemistryService()
    for club in repo.many("clubs", {}, limit=None):
        if not repo.find("club_chemistry", {"_id": club["_id"]}):
            chemistry.save(repo, club["_id"], {})

    for junior in repo.many(
        "youth_players", {"estimated_potential_capacity": {"$exists": False}}, limit=None
    ):
        repo.update(
            "youth_players",
            {"_id": junior["_id"]},
            {
                "$set": {
                    "estimated_potential_capacity": junior.get("potential", junior["strength"]),
                    "club_id": junior.get("owner_club_id"),
                }
            },
        )
