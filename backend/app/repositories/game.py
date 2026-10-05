from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument

from app.models.game import DEFAULT_RULES, FACILITIES, utcnow


class GameRepository:
    def __init__(self, database, session=None):
        self.database = database
        self.session = session

    def find(self, collection, query, projection=None):
        return self.database[collection].find_one(query, projection, session=self.session)

    def many(self, collection, query, *, limit=200, sort=None):
        cursor = self.database[collection].find(query, session=self.session)
        if sort:
            cursor = cursor.sort(sort)
        return list(cursor.limit(limit or 0))

    def ticket_income(self, club_id):
        result = list(
            self.database.financial_transactions.aggregate(
                [
                    {"$match": {"club_id": club_id, "category": "ticket_income"}},
                    {"$group": {"_id": None, "amount": {"$sum": "$amount"}}},
                ],
                session=self.session,
            )
        )
        return result[0]["amount"] if result else 0

    def search_players(self, query, listing_type=None):
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
        pipeline.append({"$limit": 200})
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
        setting = self.find("app_settings", {"key": "game_rules"})
        return {**DEFAULT_RULES, **(setting["value"] if setting else {})}

    def money(self, club_id, amount, category, reference=None):
        query = {"_id": club_id}
        if amount < 0:
            query["balance"] = {"$gte": -amount}
        if not self.update("club_finances", query, {"$inc": {"balance": amount}}):
            raise HTTPException(409, "Saldo insuficiente.")
        now = utcnow()
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
        self.insert(
            "calendar_events",
            {
                "_id": ObjectId(),
                "club_id": club_id,
                "type": event_type,
                "title": title,
                "date": date or utcnow(),
                "reference_id": reference,
            },
        )

    def initialize(self):
        old_index = self.database.clubs.index_information().get("owner_user_id_1", {})
        partial = {"owner_user_id": {"$type": "objectId"}}
        if old_index and old_index.get("partialFilterExpression") != partial:
            self.database.clubs.drop_index("owner_user_id_1")
        self.database.clubs.create_index(
            "owner_user_id", unique=True, partialFilterExpression=partial
        )
        self.database.seasons.create_index(
            "status", unique=True, partialFilterExpression={"status": "active"}
        )
        self.database.divisions.create_index("tier", unique=True)
        self.database.season_clubs.create_index([("season_id", 1), ("club_id", 1)], unique=True)
        self.database.standings.create_index(
            [("season_id", 1), ("division_id", 1), ("position", 1)]
        )
        self.database.matches.create_index([("season_id", 1), ("status", 1), ("date", 1)])
        self.database.youth_players.create_index("current_club_id")
        self.database.calendar_events.create_index([("reference_id", 1), ("club_id", 1)])
        indexes = {
            "players": [("current_club_id", False), ("owner_club_id", False)],
            "financial_transactions": [("club_id", False)],
            "calendar_events": [("club_id", False)],
            "transfer_offers": [("listing_id", False), ("buyer_club_id", False)],
            "player_loans": [("ends_at", False)],
            "bank_contracts": [("ends_at", False)],
        }
        for collection, fields in indexes.items():
            for field, unique in fields:
                self.database[collection].create_index(field, unique=unique)
        self.database.transfer_listings.create_index(
            "player_id", unique=True, partialFilterExpression={"status": "active"}
        )
        for code, name in [("BR", "Brasil"), ("PT", "Portugal"), ("AR", "Argentina")]:
            self.database.countries.update_one(
                {"_id": code}, {"$setOnInsert": {"name": name}}, upsert=True
            )
        for code, color in [("blue", "#2563eb"), ("red", "#dc2626"), ("green", "#16a34a")]:
            self.database.club_badges.update_one(
                {"_id": code},
                {"$setOnInsert": {"name": code, "color": color, "symbol": "🛡"}},
                upsert=True,
            )
        return FACILITIES
