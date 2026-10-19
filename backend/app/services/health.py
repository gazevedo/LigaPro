import logging
from os import getenv
from time import monotonic

from pymongo import timeout
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.repositories.game import GameRepository
from app.services.competition import CompetitionService

logger = logging.getLogger(__name__)


class HealthService:
    def __init__(self, database: Database):
        self.database = database

    def check(self) -> dict[str, object]:
        repository = GameRepository(self.database)
        competition = CompetitionService(repository)
        complete = False
        failure = None
        # Each committed step survives a cancelled serverless request.
        deadline = monotonic() + 4
        try:
            with timeout(5):
                self.database.command("ping")
                while monotonic() < deadline:
                    if not repository.initialize(max_steps=1):
                        continue
                    if competition.initialize_universe(max_steps=1) is not None:
                        complete = True
                        break
        except PyMongoError as error:
            if not error.timeout:
                logger.exception("Database generation step failed")
                failure = type(error).__name__
        with timeout(2):
            result = self.progress(repository, competition, complete)
        if failure:
            result["status"] = "error"
            result["initialization"]["status"] = "failed"
            result["initialization"]["error"] = failure
            result["detail"] = (
                "Não foi possível concluir esta etapa da preparação. Consulte os logs do backend."
            )
        return result

    def progress(self, repository, competition, complete):
        season = competition.current(repository)
        divisions = repository.many(
            "divisions", {"active": {"$ne": False}}, limit=None, projection={"_id": 1}
        )
        query = {
            "season_id": season["_id"] if season else None,
            "division_id": {"$in": [d["_id"] for d in divisions]},
        }
        schema = repository.schema_progress()
        schema_done = sum(step["completed"] for step in schema)
        clubs = self.database.season_clubs.count_documents(query)
        matches = self.database.matches.count_documents(query)
        target_clubs = max(1, len(divisions)) * 20
        completed_steps = schema_done + min(clubs, target_clubs) + int(complete)
        total_steps = len(schema) + target_clubs + 1
        pending_schema = next((step for step in schema if not step["completed"]), None)
        stage = (
            pending_schema["stage"]
            if pending_schema
            else "ready"
            if complete
            else "clubs"
            if clubs < target_clubs
            else "calendar"
        )
        current_step = (
            pending_schema["label"]
            if pending_schema
            else "Base concluída"
            if complete
            else f"Criar clube bot {min(clubs + 1, target_clubs)} de {target_clubs}"
            if clubs < target_clubs
            else "Gerar calendário e validar liga"
        )
        stage_steps = [
            {
                "stage": name,
                "completed": sum(step["completed"] for step in schema if step["stage"] == name),
                "total": sum(step["stage"] == name for step in schema),
            }
            for name in ("indexes", "catalogs")
        ]
        stage_steps.extend(
            [
                {"stage": "clubs", "completed": min(clubs, target_clubs), "total": target_clubs},
                {"stage": "calendar", "completed": int(complete), "total": 1},
            ]
        )
        return {
            "status": "ok" if complete else "initializing",
            "api": "ok",
            "mongodb": "ok",
            "revision": getenv("VERCEL_GIT_COMMIT_SHA"),
            "initialization": {
                "status": "ready" if complete else "running",
                "percentage": 100 if complete else min(99, completed_steps * 100 // total_steps),
                "stage": stage,
                "current_step": current_step,
                "completed_steps": completed_steps,
                "total_steps": total_steps,
                "steps": stage_steps,
            },
            "league": {
                "status": "ready" if complete else "initializing",
                "divisions": len(divisions),
                "clubs": clubs,
                "bots": self.database.standings.count_documents({**query, "is_bot": True}),
                "matches": matches,
            },
        }
