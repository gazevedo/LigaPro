import hashlib
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import Request as GoogleTransport
from google.oauth2 import id_token
from pymongo.errors import DuplicateKeyError

from app.config.settings import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    new_refresh_token,
    token_hash,
    verify_password,
)
from app.models.user import User
from app.repositories.auth import AuthRepository
from app.schemas.auth import GoogleRequest, LoginRequest, RegisterRequest, TokenResponse

INVALID_LOGIN = "E-mail ou senha inválidos."


class AuthService:
    def __init__(self, repository: AuthRepository, config: Settings):
        self.repository = repository
        self.config = config

    def check_rate_limit(self, address: str, action: str) -> None:
        now = datetime.now(UTC)
        key = hashlib.sha256(
            f"{address}:{action}:{int(now.timestamp()) // 60}".encode()
        ).hexdigest()
        if self.repository.rate_count(key, now) > self.config.auth_rate_limit_per_minute:
            raise HTTPException(
                429,
                "Muitas tentativas. Tente novamente em instantes.",
                headers={"Retry-After": "60"},
            )

    def register(self, body: RegisterRequest) -> TokenResponse:
        now = datetime.now(UTC)
        document = {
            "name": body.name,
            "email": str(body.email),
            "password_hash": hash_password(body.password),
            "auth_provider": "local",
            "google_id": None,
            "avatar_url": None,
            "email_verified": False,
            "active": True,
            "created_at": now,
            "updated_at": now,
            "last_login_at": None,
        }
        try:
            user = self.repository.create_user(document)
        except DuplicateKeyError:
            raise HTTPException(409, "Não foi possível cadastrar este e-mail.") from None
        return self.issue_session(user, body.device_id, body.device_name)

    def login(self, body: LoginRequest) -> TokenResponse:
        user = self.repository.get_by_email(str(body.email))
        valid = verify_password(body.password, user.get("password_hash") if user else None)
        if not valid or not user or not user["active"]:
            raise HTTPException(401, INVALID_LOGIN)
        return self.issue_session(user, body.device_id, body.device_name)

    def google(self, body: GoogleRequest) -> TokenResponse:
        if not self.config.google_web_client_id:
            raise HTTPException(503, "Login Google não configurado.")
        try:
            # Google verifies signature, expiration, audience and accepted issuers.
            info = id_token.verify_oauth2_token(
                body.id_token,
                GoogleTransport(),
                self.config.google_web_client_id,
            )
        except TransportError:
            raise HTTPException(503, "Validação Google indisponível.") from None
        except (ValueError, GoogleAuthError):
            raise HTTPException(401, "Credencial Google inválida.") from None
        if not info.get("sub") or not info.get("email") or info.get("email_verified") is not True:
            raise HTTPException(401, "Credencial Google inválida.")
        user = self.repository.get_by_google_id(info["sub"])
        if not user:
            email = info["email"].strip().lower()
            if self.repository.get_by_email(email):
                raise HTTPException(
                    409,
                    "Este e-mail já possui conta. Entre pelo método original; "
                    "a vinculação com Google ainda não está disponível.",
                )
            now = datetime.now(UTC)
            document = {
                "name": info.get("name") or email.split("@")[0],
                "email": email,
                "password_hash": None,
                "auth_provider": "google",
                "google_id": info["sub"],
                "avatar_url": info.get("picture"),
                "email_verified": True,
                "active": True,
                "created_at": now,
                "updated_at": now,
                "last_login_at": None,
            }
            try:
                user = self.repository.create_user(document)
            except DuplicateKeyError:
                user = self.repository.get_by_google_id(info["sub"])
                if not user:
                    raise HTTPException(409, "Conta já existente. Use o método original.") from None
        if not user["active"]:
            raise HTTPException(401, "Não foi possível autenticar.")
        return self.issue_session(user, body.device_id, body.device_name)

    def issue_session(
        self, user: dict, device_id: str | None, device_name: str | None
    ) -> TokenResponse:
        now = datetime.now(UTC)
        refresh = new_refresh_token()
        session = self.repository.create_session(
            {
                "user_id": user["_id"],
                "refresh_token_hash": token_hash(refresh),
                "device_id": device_id,
                "device_name": device_name,
                "created_at": now,
                "expires_at": now + timedelta(days=self.config.refresh_token_expire_days),
                "revoked_at": None,
                "last_used_at": now,
            }
        )
        self.repository.mark_login(user["_id"], now)
        user["last_login_at"] = now
        return self.response(user, session, refresh)

    def response(self, user: dict, session: dict, refresh: str) -> TokenResponse:
        return TokenResponse(
            access_token=create_access_token(str(user["_id"]), str(session["_id"]), self.config),
            refresh_token=refresh,
            expires_in=self.config.access_token_expire_minutes * 60,
            refresh_expires_at=session["expires_at"],
            user=User.from_document(user),
        )

    def refresh(self, token: str) -> TokenResponse:
        refresh = new_refresh_token()
        session = self.repository.rotate_session(
            token_hash(token), token_hash(refresh), datetime.now(UTC)
        )
        if not session:
            raise HTTPException(401, "Sessão inválida ou expirada.")
        user = self.repository.get_user(str(session["user_id"]))
        if not user or not user["active"]:
            self.repository.revoke(token_hash(refresh))
            raise HTTPException(401, "Sessão inválida ou expirada.")
        return self.response(user, session, refresh)

    def logout(self, token: str, access_token: str | None = None) -> None:
        if access_token:
            try:
                claims = decode_access_token(access_token, self.config)
                self.repository.revoke_session(claims["sid"], claims["sub"])
            except HTTPException:
                pass  # Refresh possession can still revoke when access has expired.
        self.repository.revoke(token_hash(token))

    def current_user(self, token: str) -> User:
        claims = decode_access_token(token, self.config)
        if not self.repository.session_active(claims["sid"], claims["sub"]):
            raise HTTPException(401, "Sessão inválida ou expirada.")
        user = self.repository.get_user(claims["sub"])
        if not user or not user["active"]:
            raise HTTPException(401, "Sessão inválida ou expirada.")
        return User.from_document(user)
