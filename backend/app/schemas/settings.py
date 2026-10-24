from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.setting import Setting


class SettingUpdate(BaseModel):
    value: Any = Field(...)


class SettingResponse(Setting):
    pass


class DatabaseResetInput(BaseModel):
    confirmation: Literal["APAGAR TODOS OS DADOS"]
