from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.database import Database

from app.config.settings import get_settings
from app.database.mongo import get_database
from app.repositories.auth import AuthRepository
from app.repositories.settings import SettingsRepository
from app.services.auth import AuthService
from app.services.health import HealthService
from app.services.settings import SettingsService

bearer = HTTPBearer(auto_error=False)


def get_settings_service(database: Database = Depends(get_database)) -> SettingsService:
    return SettingsService(SettingsRepository(database))


def get_health_service(database: Database = Depends(get_database)) -> HealthService:
    return HealthService(database)


def get_auth_service(database: Database = Depends(get_database)):
    return AuthService(AuthRepository(database), get_settings())


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    service: AuthService = Depends(get_auth_service),
):
    if credentials is None:
        raise HTTPException(401, "Autenticação necessária.", headers={"WWW-Authenticate": "Bearer"})
    return service.current_user(credentials.credentials)
