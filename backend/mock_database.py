"""Import the checked-in initial universe directly into MongoDB, once."""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from bson.json_util import JSONOptions, loads
from pymongo import MongoClient, UpdateOne

from app.models.game import round_match_time, utcnow
from app.repositories.game import GameRepository

logger = logging.getLogger(__name__)
SEED_MARKER = "mock_database_v1"
DATA_FILE = Path(__file__).with_suffix(".json")


def shift_dates(value, offset):
    if isinstance(value, datetime):
        return value + offset
    if isinstance(value, dict):
        return {key: shift_dates(item, offset) for key, item in value.items()}
    if isinstance(value, list):
        return [shift_dates(item, offset) for item in value]
    return value


def import_database(database):
    repo = GameRepository(database)
    seed = repo.find("game_state", {"_id": SEED_MARKER})
    universe = repo.find("game_state", {"_id": "initial_universe"})
    if (seed and seed.get("status") == "ready") or (universe and universe.get("status") == "ready"):
        logger.info("mock_database already initialized; preserving existing data")
        return False
    if not seed and database.clubs.find_one({}, {"_id": 1}):
        # Another cold instance may have claimed/imported the seed meanwhile.
        seed = repo.find("game_state", {"_id": SEED_MARKER})
        if not seed:
            raise RuntimeError(
                "A base contém clubes. A importação não sobrescreve uma liga existente."
            )
    payload = loads(DATA_FILE.read_text(), json_options=JSONOptions(tz_aware=True))
    if payload["version"] != 1:
        raise ValueError("Versão do mock database não suportada")
    database.game_state.update_one(
        {"_id": SEED_MARKER},
        {"$setOnInsert": {"status": "importing", "started_at": utcnow()}},
        upsert=True,
    )
    seed = repo.find("game_state", {"_id": SEED_MARKER})
    database.game_state.update_one(
        {"_id": "initial_universe"},
        {"$setOnInsert": {"status": "preparing"}},
        upsert=True,
    )
    offset = seed["started_at"] - payload["anchor"]
    kickoff_offset = (
        round_match_time(seed["started_at"] + timedelta(minutes=15)) - seed["started_at"]
    )
    match_dates = {
        document["_id"]: round_match_time(document["date"] + offset + kickoff_offset)
        for collection in ("matches", "competition_matches", "friendly_matches")
        for document in payload["collections"].get(collection, [])
        if document.get("status") in {"scheduled", "pending"}
    }
    repo.initialize()
    universe_marker = None
    for collection, documents in payload["collections"].items():
        documents = shift_dates(documents, offset)
        for document in documents:
            if (
                collection in ("matches", "competition_matches", "friendly_matches")
                and document["_id"] in match_dates
            ):
                document["date"] = match_dates[document["_id"]]
            elif collection == "calendar_events" and document.get("reference_id") in match_dates:
                document["date"] = match_dates[document["reference_id"]]
        if collection == "game_state":
            universe_marker = next(doc for doc in documents if doc["_id"] == "initial_universe")
            documents = [doc for doc in documents if doc["_id"] != "initial_universe"]
        if documents:
            database[collection].bulk_write(
                [
                    UpdateOne({"_id": doc["_id"]}, {"$setOnInsert": doc}, upsert=True)
                    for doc in documents
                ]
            )
        logger.info("mock_database collection=%s documents=%s", collection, len(documents))
    # Publish readiness only after all collections have been imported.
    database.game_state.update_one(
        {"_id": "initial_universe"},
        {"$set": universe_marker},
        upsert=True,
    )
    database.game_state.update_one(
        {"_id": SEED_MARKER},
        {"$set": {"status": "ready", "completed_at": utcnow()}},
    )
    logger.info("mock_database import complete: 20 bots, 500 players, 380 matches")
    return True


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # Only database access is needed: no API, authentication secret or HTTP call.
    from dotenv import load_dotenv

    load_dotenv()
    uri = os.environ.get("MONGODB_CONNECTION_STRING")
    name = os.environ.get("MONGODB_DATABASE_NAME")
    if not uri or not name:
        raise SystemExit("Configure MONGODB_CONNECTION_STRING e MONGODB_DATABASE_NAME.")
    with MongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=5000) as client:
        import_database(client[name])


if __name__ == "__main__":
    main()
