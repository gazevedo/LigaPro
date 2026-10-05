from datetime import datetime

from pydantic import BaseModel


class User(BaseModel):
    id: str
    name: str
    email: str
    auth_provider: str
    avatar_url: str | None = None
    email_verified: bool
    active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None

    @classmethod
    def from_document(cls, document: dict) -> "User":
        values = {**document, "id": str(document["_id"])}
        # MongoDB stores UTC datetimes at millisecond precision.
        for field in ["created_at", "updated_at", "last_login_at"]:
            if values.get(field):
                date = values[field]
                values[field] = date.replace(microsecond=date.microsecond // 1000 * 1000)
        return cls(**values)
