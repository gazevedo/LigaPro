from fastapi import Depends
from pymongo.database import Database

from app.database.mongo import get_database
from app.repositories.settings import SettingsRepository
from app.services.health import HealthService
from app.services.settings import SettingsService


def get_settings_service(database: Database = Depends(get_database)) -> SettingsService:
    return SettingsService(SettingsRepository(database))


def get_health_service(database: Database = Depends(get_database)) -> HealthService:
    return HealthService(database)
