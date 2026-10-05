from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Setting(BaseModel):
    id: str
    key: str
    value: Any
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_document(cls, document: dict) -> "Setting":
        return cls(**{**document, "id": str(document["_id"])})
