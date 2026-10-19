from fastapi import Request
from pymongo import MongoClient
from pymongo.database import Database

from app.config.settings import Settings, get_settings


def create_client(settings: Settings) -> MongoClient:
    return MongoClient(
        settings.mongodb_connection_string,
        tz_aware=True,
        serverSelectionTimeoutMS=3000,
        connectTimeoutMS=3000,
    )


def get_database(request: Request) -> Database:
    state = request.app.state
    if not getattr(state, "database_ready", False):
        # Some serverless adapters serve ASGI requests without running lifespan.
        with state.database_lock:
            if not getattr(state, "database_ready", False):
                from app.main import initialize_database

                config = get_settings()
                client = create_client(config)
                database = client[config.mongodb_database_name]
                try:
                    initialize_database(database)
                except Exception:
                    client.close()
                    raise
                state.database_client = client
                state.database = database
                state.database_ready = True
    return state.database
