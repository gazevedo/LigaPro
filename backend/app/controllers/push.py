"""Authenticated browser subscriptions for match reminders."""

import base64
import hashlib
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from app.api.dependencies import get_current_user
from app.config.settings import get_settings
from app.database.mongo import get_database
from app.models.game import utcnow

router = APIRouter(prefix="/push", tags=["push"])
User = Annotated[object, Depends(get_current_user)]
Database = Annotated[object, Depends(get_database)]


class Subscription(BaseModel):
    endpoint: str = Field(max_length=2048)
    keys: dict[str, str]

    @field_validator("endpoint")
    @classmethod
    def valid_endpoint(cls, value):
        url = urlsplit(value)
        hosts = {"fcm.googleapis.com", "updates.push.services.mozilla.com", "web.push.apple.com"}
        if (
            url.scheme != "https"
            or url.hostname not in hosts
            or url.port not in (None, 443)
            or url.username
            or url.password
        ):
            raise ValueError("Serviço de notificações não suportado.")
        return value

    @field_validator("keys")
    @classmethod
    def valid_keys(cls, value):
        for name, size in (("auth", 16), ("p256dh", 65)):
            encoded = value.get(name, "")
            if (
                len(encoded) > 100
                or len(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))) != size
            ):
                raise ValueError("Chaves de notificação inválidas.")
        return {name: value[name] for name in ("auth", "p256dh")}


@router.get("/config")
def config(user: User):
    settings = get_settings()
    return {
        "public_key": settings.web_push_public_key
        if settings.web_push_private_key and settings.web_push_subject
        else None
    }


@router.put("/subscription")
def subscribe(body: Subscription, user: User, db: Database):
    identity = hashlib.sha256(body.endpoint.encode()).hexdigest()
    db.push_subscriptions.update_one(
        {"_id": identity},
        {
            "$set": {
                "user_id": str(user.id),
                "subscription": body.model_dump(),
                "updated_at": utcnow(),
            }
        },
        upsert=True,
    )
    return {"enabled": True}


@router.delete("/subscription")
def unsubscribe(body: Subscription, user: User, db: Database):
    db.push_subscriptions.delete_one(
        {"_id": hashlib.sha256(body.endpoint.encode()).hexdigest(), "user_id": str(user.id)}
    )
    return {"enabled": False}
