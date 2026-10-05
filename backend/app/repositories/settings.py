from datetime import UTC, datetime
from typing import Any

from pymongo import ReturnDocument
from pymongo.database import Database

from app.models.setting import Setting


class SettingsRepository:
    def __init__(self, database: Database):
        self.collection = database["app_settings"]

    def list(self) -> list[Setting]:
        return [Setting.from_document(doc) for doc in self.collection.find().sort("key", 1)]

    def get(self, key: str) -> Setting | None:
        document = self.collection.find_one({"key": key})
        return Setting.from_document(document) if document else None

    def put(self, key: str, value: Any) -> Setting:
        now = datetime.now(UTC)
        document = self.collection.find_one_and_update(
            {"key": key},
            {"$set": {"value": value, "updated_at": now},
             "$setOnInsert": {"key": key, "created_at": now}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return Setting.from_document(document)
