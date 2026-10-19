import json
from hashlib import sha256

from bson import ObjectId
from fastapi import HTTPException
from pymongo import IndexModel, ReturnDocument, UpdateOne
from pymongo.errors import OperationFailure

from app.models.catalog import BADGES, COUNTRIES
from app.models.game import DEFAULT_RULES, utcnow


class GameRepository:
    def __init__(self, database, session=None):
        self.database = database
        self.session = session
        self._rules = None

    def find(self, collection, query, projection=None):
        return self.database[collection].find_one(query, projection, session=self.session)

    def many(self, collection, query, *, limit=200, sort=None, projection=None):
        cursor = self.database[collection].find(query, projection, session=self.session)
        if sort:
            cursor = cursor.sort(sort)
        return list(cursor.limit(limit or 0))

    def ticket_income(self, club_id):
        result = list(
            self.database.financial_transactions.aggregate(
                [
                    {
                        "$match": {
                            "club_id": club_id,
                            "category": {"$in": ["ticket_income", "ticketing"]},
                        }
                    },
                    {"$group": {"_id": None, "amount": {"$sum": "$amount"}}},
                ],
                session=self.session,
            )
        )
        return result[0]["amount"] if result else 0

    def search_players(self, query, listing_type=None, sort="value_asc"):
        pipeline = [
            {"$match": query},
            {
                "$lookup": {
                    "from": "transfer_listings",
                    "let": {"player": "$_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {"$eq": ["$player_id", "$$player"]},
                                "status": "active",
                                "negotiation_only": {"$ne": True},
                            }
                        }
                    ],
                    "as": "listings",
                }
            },
            {"$set": {"listing": {"$ifNull": [{"$arrayElemAt": ["$listings", 0]}, None]}}},
            {"$unset": "listings"},
        ]
        if listing_type:
            pipeline.append({"$match": {"listing.type": listing_type}})
        field = "strength" if sort.startswith("strength") else "market_value"
        direction = -1 if sort.endswith("desc") else 1
        pipeline.append(
            {
                "$set": {
                    "sort_value": {
                        "$ifNull": [f"${field}", "$overall" if field == "strength" else "$value"]
                    }
                }
            }
        )
        pipeline.extend(
            [
                {"$sort": {"sort_value": direction, "_id": 1}},
                {"$limit": 200},
                {"$unset": "sort_value"},
            ]
        )
        return list(self.database.players.aggregate(pipeline, session=self.session))

    def insert(self, collection, document):
        self.database[collection].insert_one(document, session=self.session)
        return document

    def insert_many(self, collection, documents):
        self.database[collection].insert_many(documents, session=self.session)

    def update(self, collection, query, changes):
        return self.database[collection].find_one_and_update(
            query, changes, return_document=ReturnDocument.AFTER, session=self.session
        )

    def update_many(self, collection, query, changes):
        return self.database[collection].update_many(query, changes, session=self.session)

    def transaction(self, callback):
        with self.database.client.start_session() as session:
            return session.with_transaction(
                lambda active: callback(GameRepository(self.database, active))
            )

    def document(self, collection, identity):
        if not ObjectId.is_valid(identity):
            raise HTTPException(404, "Registro não encontrado.")
        document = self.find(collection, {"_id": ObjectId(identity)})
        if not document:
            raise HTTPException(404, "Registro não encontrado.")
        return document

    def owned(self, user_id):
        club = self.find("clubs", {"owner_user_id": ObjectId(user_id)})
        if not club:
            raise HTTPException(403, "Crie seu clube para administrar o jogo.")
        return club

    def rules(self):
        if self.session is not None and self._rules is not None:
            return dict(self._rules)
        setting = self.find("app_settings", {"key": "game_rules"})
        rules = {**DEFAULT_RULES, **(setting["value"] if setting else {})}
        if self.session is not None:
            self._rules = rules
        return dict(rules)

    def money(
        self, club_id, amount, category, reference=None, *, allow_overdraft=False, effective_at=None
    ):
        query = {"_id": club_id}
        if amount < 0 and not allow_overdraft:
            query["balance"] = {"$gte": -amount}
        balance = {"$add": [{"$ifNull": ["$balance", 0]}, amount]}
        if not self.update(
            "club_finances",
            query,
            [{"$set": {"balance": balance, "cash_balance": balance, "updated_at": utcnow()}}],
        ):
            raise HTTPException(409, "Saldo insuficiente.")
        now = effective_at or utcnow()
        self.insert(
            "financial_transactions",
            {
                "_id": ObjectId(),
                "club_id": club_id,
                "amount": amount,
                "category": category,
                "reference_id": reference,
                "created_at": now,
            },
        )
        self.event(club_id, "financial", category, now, reference)

    def event(self, club_id, event_type, title, date=None, reference=None):
        from app.services.news import NewsService

        # Future calendar reminders are not completed game events.
        if date is None or date <= utcnow():
            NewsService.publish(self, event_type, title, club_id, reference, now=date)
        self.insert(
            "calendar_events",
            {
                "_id": ObjectId(),
                "club_id": club_id,
                "type": event_type,
                "kind": ("cup_match" if "Copa" in title else "league_match")
                if event_type == "match"
                else {"training": "training_event"}.get(event_type, event_type),
                "title": title,
                "date": date or utcnow(),
                "reference_id": reference,
            },
        )

    SCHEMA_MARKER = "database_schema_v1"

    def _schema_steps(self):
        index = IndexModel
        indexes = {
            "app_settings": [index("key", unique=True)],
            "users": [
                index("email", unique=True),
                index(
                    "name_key",
                    unique=True,
                    partialFilterExpression={"name_key": {"$type": "string"}},
                ),
                index(
                    "google_id",
                    unique=True,
                    partialFilterExpression={"google_id": {"$type": "string"}},
                ),
            ],
            "user_sessions": [
                index("refresh_token_hash", unique=True),
                index("user_id"),
                index("expires_at", expireAfterSeconds=0),
            ],
            "auth_rate_limits": [index("expires_at", expireAfterSeconds=0)],
            "push_subscriptions": [index("user_id")],
            "push_deliveries": [index("expires_at", expireAfterSeconds=0)],
            "match_commands": [index([("match_id", 1), ("sequence_number", 1)], unique=True)],
            "match_participants": [index([("match_id", 1), ("user_id", 1)], unique=True)],
            "match_live_snapshots": [index([("match_id", 1), ("minute", 1)], unique=True)],
            "club_loans": [index([("club_id", 1), ("status", 1), ("next_installment_at", 1)])],
            "news_items": [index([("club_id", 1), ("created_at", -1)])],
            "news_reads": [index([("user_id", 1), ("news_id", 1)], unique=True)],
            "match_events": [index([("match_id", 1), ("sequence", 1)], unique=True)],
            "player_development_history": [
                index([("season_id", 1), ("player_id", 1)], unique=True)
            ],
            "sponsor_offers": [index([("club_id", 1), ("status", 1)])],
            "friendly_matches": [index([("season_id", 1), ("status", 1), ("date", 1)])],
            "clubs": [
                index(
                    "owner_user_id",
                    unique=True,
                    partialFilterExpression={"owner_user_id": {"$type": "objectId"}},
                )
            ],
            "seasons": [index("status", unique=True, partialFilterExpression={"status": "active"})],
            "club_tactics": [index("club_id", unique=True)],
            "divisions": [index("tier", unique=True)],
            "season_clubs": [
                index([("season_id", 1), ("club_id", 1)], unique=True),
                index([("club_id", 1), ("season_id", 1)]),
            ],
            "standings": [index([("season_id", 1), ("division_id", 1), ("position", 1)])],
            "matches": [index([("season_id", 1), ("status", 1), ("date", 1)])],
            "player_contracts": [
                index(
                    "player_id",
                    unique=True,
                    partialFilterExpression={"status": {"$in": ["active", "expiring"]}},
                ),
                index([("status", 1), ("next_salary_at", 1)]),
                index([("status", 1), ("expiring_at", 1)]),
                index([("club_id", 1), ("status", 1)]),
            ],
            "contract_history": [index([("player_id", 1), ("created_at", -1)])],
            "club_chemistry": [index("club_id", unique=True)],
            "player_season_stats": [
                index([("player_id", 1), ("club_id", 1), ("season_id", 1)], unique=True),
                index([("season_id", 1), ("goals", -1)]),
            ],
            "player_match_ratings": [
                index([("match_id", 1), ("player_id", 1)], unique=True),
                index([("player_id", 1), ("match_id", 1)]),
            ],
            "club_finance_months": [index([("club_id", 1), ("end", 1)], unique=True)],
            "player_market_value_history": [index([("player_id", 1), ("created_at", -1)])],
            "club_fan_history": [index([("club_id", 1), ("created_at", -1)])],
            "club_ranking_history": [index([("club_id", 1), ("created_at", -1)])],
            "competitions": [index([("season_id", 1), ("name", 1)], unique=True)],
            "competition_entries": [index([("competition_id", 1), ("club_id", 1)], unique=True)],
            "competition_rounds": [index([("competition_id", 1), ("number", 1)], unique=True)],
            "competition_matches": [index([("competition_id", 1), ("status", 1), ("date", 1)])],
            "player_injuries": [index([("player_id", 1), ("status", 1)])],
            "bot_decisions": [index([("club_id", 1), ("created_at", -1)])],
            "transfer_offers": [
                index([("status", 1), ("expires_at", 1)]),
                index("listing_id"),
                index("buyer_club_id"),
            ],
            "youth_players": [index("current_club_id")],
            "calendar_events": [index([("reference_id", 1), ("club_id", 1)]), index("club_id")],
            "players": [index("current_club_id"), index("owner_club_id")],
            "financial_transactions": [index("club_id")],
            "player_loans": [index("ends_at")],
            "bank_contracts": [index("ends_at")],
            "transfer_listings": [
                index("player_id", unique=True, partialFilterExpression={"status": "active"})
            ],
        }
        for collection in ("matches", "competition_matches", "friendly_matches"):
            for side in ("home", "away"):
                indexes[collection].append(index([(f"{side}_club_id", 1), ("date", 1)]))
                if collection == "matches":
                    indexes[collection].append(index([(f"{side}_slot_id", 1), ("date", 1)]))
        steps = []
        for collection, models in indexes.items():
            fingerprint = sha256(
                json.dumps([model.document for model in models], sort_keys=True).encode()
            ).hexdigest()[:16]
            steps.append(
                (
                    f"indexes:{collection}:{fingerprint}",
                    "indexes",
                    f"Índices de {collection}",
                    lambda collection=collection, models=models: self._create_schema_indexes(
                        collection, models
                    ),
                )
            )
        steps.append(
            (
                "catalog:countries:v1",
                "catalogs",
                "Catálogo de países",
                lambda: self.database.countries.bulk_write(
                    [
                        UpdateOne({"_id": code}, {"$set": {"name": name}}, upsert=True)
                        for code, name in COUNTRIES
                    ]
                ),
            )
        )
        steps.append(
            (
                "catalog:badges:v1",
                "catalogs",
                "Catálogo de escudos",
                lambda: self.database.club_badges.bulk_write(
                    [
                        UpdateOne(
                            {"_id": badge["id"]},
                            {"$set": {key: value for key, value in badge.items() if key != "id"}},
                            upsert=True,
                        )
                        for badge in BADGES
                    ]
                ),
            )
        )
        return steps

    def _create_schema_indexes(self, collection, models):
        if collection == "clubs":
            old = self.database.clubs.index_information().get("owner_user_id_1", {})
            partial = {"owner_user_id": {"$type": "objectId"}}
            if old and old.get("partialFilterExpression") != partial:
                try:
                    self.database.clubs.drop_index("owner_user_id_1")
                except OperationFailure as error:
                    if error.code != 27:
                        raise
        self.database[collection].create_indexes(models)

    def schema_progress(self):
        steps = self._schema_steps()
        state = self.find("game_state", {"_id": self.SCHEMA_MARKER}) or {}
        completed = set(state.get("completed", []))
        return [
            {"id": key, "stage": stage, "label": label, "completed": key in completed}
            for key, stage, label, _ in steps
        ]

    def initialize(self, max_steps=None):
        steps = self._schema_steps()
        state = self.find("game_state", {"_id": self.SCHEMA_MARKER}) or {}
        completed = set(state.get("completed", []))
        performed = 0
        for key, stage, label, operation in steps:
            if key in completed:
                continue
            operation()
            self.database.game_state.update_one(
                {"_id": self.SCHEMA_MARKER},
                {
                    "$addToSet": {"completed": key},
                    "$set": {"stage": stage, "last_step": label, "updated_at": utcnow()},
                    "$setOnInsert": {"status": "preparing"},
                },
                upsert=True,
            )
            completed.add(key)
            performed += 1
            if max_steps is not None and performed >= max_steps:
                break
        ready = all(key in completed for key, *_ in steps)
        if ready and state.get("status") != "ready":
            self.database.game_state.update_one(
                {"_id": self.SCHEMA_MARKER}, {"$set": {"status": "ready"}}
            )
        return ready
