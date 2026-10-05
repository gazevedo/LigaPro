from fastapi import Request
from pymongo import MongoClient
from pymongo.database import Database

from app.config.settings import Settings


def create_client(settings: Settings) -> MongoClient:
    return MongoClient(
        settings.mongodb_connection_string,
        tz_aware=True,
        serverSelectionTimeoutMS=3000,
        connectTimeoutMS=3000,
    )


def get_database(request: Request) -> Database:
    return request.app.state.database
