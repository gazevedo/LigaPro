from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import User

Password = Annotated[str, Field(min_length=8, max_length=128)]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    device_id: str | None = Field(default=None, max_length=128)
    device_name: str | None = Field(default=None, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class RegisterRequest(LoginRequest):
    name: str = Field(min_length=1, max_length=100)
    password: Password

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name is required")
        return value


class GoogleRequest(BaseModel):
    id_token: str = Field(min_length=1, max_length=10000)
    device_id: str | None = Field(default=None, max_length=128)
    device_name: str | None = Field(default=None, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_at: datetime
    user: User
