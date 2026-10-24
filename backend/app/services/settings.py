from datetime import timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.config.settings import get_settings
from app.models.game import utcnow
from app.models.setting import Setting
from app.repositories.settings import SettingsRepository


class SettingsService:
    def __init__(self, repository: SettingsRepository):
        self.repository = repository

    def list(self) -> list[Setting]:
        return self.repository.list()

    def get(self, key: str) -> Setting:
        setting = self.repository.get(key)
        if setting is None:
            raise HTTPException(status_code=404, detail="Setting not found")
        return setting

    def put(self, key: str, value: Any) -> Setting:
        if key == "game_rules":
            raise HTTPException(403, "Regras do jogo são administradas no servidor.")
        return self.repository.put(key, value)

    @staticmethod
    def can_reset_database(user):
        email = get_settings().database_reset_admin_email
        return bool(email and user.email.casefold() == email.strip().casefold())

    def reset_database(self, user):
        if not self.can_reset_database(user):
            raise HTTPException(403, "Somente o administrador pode reinicializar o banco de dados.")
        from bson import ObjectId

        from app.repositories.game import GameRepository
        from mock_database import import_database

        database = self.repository.collection.database
        now, operation_id = utcnow(), uuid4().hex
        marker = {"_id": "database_reset"}
        try:
            lease = database.game_state.find_one_and_update(
                {**marker, "$or": [{"status": {"$ne": "running"}}, {"expires_at": {"$lte": now}}]},
                {
                    "$set": {
                        "status": "running",
                        "operation_id": operation_id,
                        "expires_at": now + timedelta(minutes=10),
                        "started_at": now,
                    }
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            raise HTTPException(409, "Uma reinicialização já está em andamento.") from None
        if not lease:
            raise HTTPException(409, "Uma reinicialização já está em andamento.")
        owner = ObjectId(user.id)
        collections = [
            name for name in database.list_collection_names() if not name.startswith("system.")
        ]
        try:

            def clear(repo):
                # Fence simulations/registration against the destructive transaction.
                from app.services.competition import CompetitionService

                CompetitionService.lock(repo)
                for name in collections:
                    query = {}
                    if name == "game_state":
                        query = {"_id": {"$nin": ["database_reset", "database_schema_v1"]}}
                    elif name == "users":
                        # Keep the administrator authenticated if seeding fails and needs retry.
                        query = {"_id": {"$ne": owner}}
                    elif name == "user_sessions":
                        query = {"user_id": {"$ne": owner}}
                    database[name].delete_many(query, session=repo.session)
                database.game_state.update_one(
                    {"_id": "initial_universe"},
                    {"$set": {"status": "preparing"}},
                    upsert=True,
                    session=repo.session,
                )

            GameRepository(database).transaction(clear)
            import_database(database)
            if not database.game_state.find_one({"_id": "initial_universe", "status": "ready"}):
                raise RuntimeError("A base inicial não ficou pronta.")

            # Users and sessions are removed only after a successful import.
            def finish(repo):
                database.users.delete_many({}, session=repo.session)
                database.user_sessions.delete_many({}, session=repo.session)
                database.game_state.update_one(
                    {**marker, "operation_id": operation_id},
                    {"$set": {"status": "completed", "finished_at": utcnow()}},
                    session=repo.session,
                )

            GameRepository(database).transaction(finish)
        except Exception:
            database.game_state.update_one(
                {**marker, "operation_id": operation_id},
                {"$set": {"status": "failed", "finished_at": utcnow()}},
            )
            raise
        return {"status": "ready"}
