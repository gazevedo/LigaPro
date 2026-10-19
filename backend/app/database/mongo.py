from fastapi import HTTPException, Request
from pymongo import MongoClient, timeout
from pymongo.database import Database

from app.config.settings import Settings, get_settings


def create_client(settings: Settings) -> MongoClient:
    return MongoClient(
        settings.mongodb_connection_string,
        tz_aware=True,
        serverSelectionTimeoutMS=3000,
        connectTimeoutMS=3000,
        socketTimeoutMS=5000,
    )


def get_database(request: Request) -> Database:
    state = request.app.state
    if not getattr(state, "database_ready", False):
        # Some serverless adapters serve ASGI requests without running lifespan.
        if not state.database_lock.acquire(timeout=1):
            raise HTTPException(503, "O servidor está inicializando. Tente novamente em instantes.")
        try:
            if not getattr(state, "database_ready", False):
                from app.main import initialize_database

                config = get_settings()
                client = create_client(config)
                database = client[config.mongodb_database_name]
                try:
                    with timeout(8):
                        initialize_database(database, prepare_universe=False)
                except Exception:
                    client.close()
                    raise
                state.database_client = client
                state.database = database
                state.database_ready = True
        finally:
            state.database_lock.release()
    return state.database
