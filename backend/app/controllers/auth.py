from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import bearer, get_auth_service, get_current_user
from app.models.user import User
from app.schemas.auth import (
    GoogleRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
Service = Annotated[AuthService, Depends(get_auth_service)]


def limit(request: Request, service: AuthService, action: str):
    # Only the trusted socket address is used; client-provided forwarding headers are ignored.
    service.check_rate_limit(request.client.host if request.client else "unknown", action)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, request: Request, service: Service):
    limit(request, service, "register")
    return service.register(body)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, service: Service):
    limit(request, service, "login")
    return service.login(body)


@router.post("/google", response_model=TokenResponse)
def google(body: GoogleRequest, request: Request, service: Service):
    limit(request, service, "google")
    return service.google(body)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, request: Request, service: Service):
    limit(request, service, "refresh")
    return service.refresh(body.refresh_token)


@router.post("/logout", status_code=204)
def logout(
    body: RefreshRequest,
    service: Service,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
):
    service.logout(body.refresh_token, credentials.credentials if credentials else None)
    return Response(status_code=204)


@router.get("/me", response_model=User)
def me(user: Annotated[User, Depends(get_current_user)]):
    return user
