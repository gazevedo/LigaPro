from typing import Any

from pydantic import BaseModel, Field

from app.models.setting import Setting


class SettingUpdate(BaseModel):
    value: Any = Field(...)


class SettingResponse(Setting):
    pass
