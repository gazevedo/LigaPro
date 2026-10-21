"""One finite game tick for an external scheduler, without an HTTP server or JWT."""

import logging
import os

from pymongo import MongoClient

from app.models.game import utcnow
from app.repositories.game import GameRepository
from app.services.game import process_due
from app.services.game_scheduler import MATCH_COLLECTIONS

logger = logging.getLogger(__name__)


def run_once(database):
    repository = GameRepository(database)
    if not repository.find("game_state", {"_id": "initial_universe", "status": "ready"}):
        raise RuntimeError(
            "A base do jogo ainda não está pronta. Inicialize o backend antes do job."
        )
    started = utcnow()

    def count(query):
        return sum(database[name].count_documents(query) for name in MATCH_COLLECTIONS)

    due_query = {"status": "scheduled", "date": {"$lte": started}}
    before = count({"status": "completed"})
    due_before = count(due_query)
    marker = {"_id": "scheduled_match_job"}
    database.game_state.update_one(
        marker, {"$set": {"status": "running", "started_at": started}}, upsert=True
    )
    try:
        process_due(repository)
        result = {
            "completed_matches": count({"status": "completed"}) - before,
            "due_before": due_before,
            "remaining_due": count(due_query),
        }
        if due_before and result["remaining_due"] and not result["completed_matches"]:
            raise RuntimeError(
                "Há jogos vencidos, mas nenhum foi concluído. Consulte os erros do job."
            )
    except Exception as error:
        database.game_state.update_one(
            marker,
            {
                "$set": {
                    "status": "failed",
                    "finished_at": utcnow(),
                    "error_type": type(error).__name__,
                }
            },
        )
        raise
    database.game_state.update_one(
        marker,
        {
            "$set": {"status": "completed", "finished_at": utcnow(), **result},
            "$unset": {"error_type": ""},
        },
    )
    logger.info("scheduled_match_job completed=%s due_before=%s remaining_due=%s", *result.values())
    return result


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    uri = os.environ.get("MONGODB_CONNECTION_STRING")
    name = os.environ.get("MONGODB_DATABASE_NAME")
    if not uri or not name:
        raise SystemExit("Configure MONGODB_CONNECTION_STRING e MONGODB_DATABASE_NAME no job.")
    with MongoClient(
        uri,
        tz_aware=True,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=30000,
    ) as client:
        run_once(client[name])


if __name__ == "__main__":
    main()
