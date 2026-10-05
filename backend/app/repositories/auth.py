from datetime import UTC, datetime, timedelta

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.database import Database


class AuthRepository:
    def __init__(self, database: Database):
        self.users = database["users"]
        self.sessions = database["user_sessions"]
        self.limits = database["auth_rate_limits"]

    def get_by_email(self, email: str) -> dict | None:
        return self.users.find_one({"email": email})

    def get_by_google_id(self, google_id: str) -> dict | None:
        return self.users.find_one({"google_id": google_id})

    def get_user(self, user_id: str) -> dict | None:
        if not ObjectId.is_valid(user_id):
            return None
        return self.users.find_one({"_id": ObjectId(user_id)}, {"password_hash": 0})

    def create_user(self, document: dict) -> dict:
        document["_id"] = self.users.insert_one(document).inserted_id
        return document

    def mark_login(self, user_id: ObjectId, now: datetime) -> None:
        self.users.update_one({"_id": user_id}, {"$set": {"last_login_at": now}})

    def create_session(self, document: dict) -> dict:
        document["_id"] = self.sessions.insert_one(document).inserted_id
        return document

    def rotate_session(self, old_hash: str, new_hash: str, now: datetime) -> dict | None:
        return self.sessions.find_one_and_update(
            {"refresh_token_hash": old_hash, "revoked_at": None, "expires_at": {"$gt": now}},
            {"$set": {"refresh_token_hash": new_hash, "last_used_at": now}},
            return_document=ReturnDocument.AFTER,
        )

    def session_active(self, session_id: str, user_id: str) -> bool:
        if not ObjectId.is_valid(session_id) or not ObjectId.is_valid(user_id):
            return False
        return (
            self.sessions.find_one(
                {
                    "_id": ObjectId(session_id),
                    "user_id": ObjectId(user_id),
                    "revoked_at": None,
                    "expires_at": {"$gt": datetime.now(UTC)},
                },
                {"_id": 1},
            )
            is not None
        )

    def revoke(self, refresh_hash: str) -> None:
        self.sessions.update_one(
            {"refresh_token_hash": refresh_hash, "revoked_at": None},
            {"$set": {"revoked_at": datetime.now(UTC)}},
        )

    def rate_count(self, key: str, now: datetime) -> int:
        document = self.limits.find_one_and_update(
            {"_id": key},
            {"$inc": {"count": 1}, "$setOnInsert": {"expires_at": now + timedelta(minutes=2)}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return document["count"]

    def revoke_session(self, session_id: str, user_id: str) -> None:
        if not ObjectId.is_valid(session_id) or not ObjectId.is_valid(user_id):
            return
        self.sessions.update_one(
            {"_id": ObjectId(session_id), "user_id": ObjectId(user_id), "revoked_at": None},
            {"$set": {"revoked_at": datetime.now(UTC)}},
        )
