from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import require_active_user
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegistrationRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService, user_response

router = APIRouter(prefix="/auth", tags=["authentication"])


def get_auth_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(session, settings)


AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegistrationRequest, service: AuthServiceDependency) -> UserResponse:
    return service.register(request)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, service: AuthServiceDependency) -> TokenResponse:
    return service.login(request)


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: RefreshRequest, service: AuthServiceDependency) -> TokenResponse:
    return service.refresh(request.refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(request: LogoutRequest, service: AuthServiceDependency) -> MessageResponse:
    service.logout(request.refresh_token)
    return MessageResponse(message="Logged out.")


@router.get("/me", response_model=UserResponse)
def current_user(user: Annotated[User, Depends(require_active_user)]) -> UserResponse:
    return user_response(user)
