from typing import Any

from fastapi import HTTPException

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
        return self.repository.put(key, value)
