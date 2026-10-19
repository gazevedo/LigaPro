import logging
from datetime import timedelta
from os import getenv
from time import monotonic, perf_counter
from uuid import uuid4

from pymongo import timeout
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.models.game import utcnow
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
        request_id = uuid4().hex[:12]
        started = perf_counter()
        logger.info("database_generation request=%s event=start", request_id)
        # Bound each step separately: a bot must not inherit an almost expired
        # schema budget, otherwise its entire transaction is rolled back.
        deadline = monotonic() + 4
        try:
            with timeout(3):
                self.database.command("ping")
            while monotonic() < deadline:
                with timeout(5):
                    schema_ready = repository.initialize(max_steps=1)
                if not schema_ready:
                    continue
                logger.info("database_generation request=%s event=league_start", request_id)
                outcome = self.advance_league(competition, request_id)
                logger.info("database_generation request=%s event=league_finished", request_id)
                if outcome is not None:
                    complete = True
                # One league transaction per request keeps response time bounded.
                break
        except PyMongoError as error:
            logger.exception(
                "database_generation request=%s event=%s elapsed_ms=%d error=%s",
                request_id,
                "timeout" if error.timeout else "failed",
                (perf_counter() - started) * 1000,
                type(error).__name__,
            )
            if not error.timeout:
                failure = type(error).__name__
        with timeout(2):
            result = self.progress(repository, competition, complete)
        progress = result["initialization"]
        logger.info(
            "database_generation request=%s event=progress stage=%s percentage=%s "
            "completed=%s total=%s current_step=%s elapsed_ms=%d",
            request_id,
            progress["stage"],
            progress["percentage"],
            progress["completed_steps"],
            progress["total_steps"],
            progress["current_step"],
            (perf_counter() - started) * 1000,
        )
        if failure:
            result["status"] = "error"
            result["initialization"]["status"] = "failed"
            result["initialization"]["error"] = failure
            result["detail"] = (
                "Não foi possível concluir esta etapa da preparação. Consulte os logs do backend."
            )
        return result

    def advance_league(self, competition, owner):
        # A persisted lease coordinates separate Vercel instances, unlike a
        # process-local mutex. A killed invocation releases it by expiry.
        now = utcnow()
        try:
            self.database.game_state.find_one_and_update(
                {
                    "_id": "database_generation_lease",
                    "$or": [{"expires_at": {"$lte": now}}, {"expires_at": {"$exists": False}}],
                },
                {"$set": {"owner": owner, "expires_at": now + timedelta(seconds=60)}},
                upsert=True,
            )
        except DuplicateKeyError:
            logger.info("database_generation request=%s event=busy", owner)
            return None
        try:
            logger.info("database_generation request=%s event=lease_acquired", owner)
            with timeout(12):
                return competition.initialize_universe(max_steps=1)
        finally:
            # Use a fresh budget even when the transaction exhausted its own.
            try:
                with timeout(1):
                    self.database.game_state.delete_one(
                        {"_id": "database_generation_lease", "owner": owner}
                    )
            except PyMongoError:
                logger.exception(
                    "database_generation request=%s event=lease_release_failed", owner
                )

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
