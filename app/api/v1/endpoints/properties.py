from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.auth_dependencies import bearer, require_active_user, require_authenticated_user
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models.property import PropertyStatus
from app.models.user import User
from app.schemas.property import (
    PropertyCreateRequest,
    PropertyResponse,
    PropertySummaryResponse,
    PropertyUpdateRequest,
)
from app.services.property_service import PropertyService

router = APIRouter(prefix="/properties", tags=["Properties"])
Db = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(require_active_user)]


def optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Db,
    settings: Annotated[Settings, Depends(get_settings)],
) -> User | None:
    if credentials is None:
        return None
    return require_authenticated_user(credentials, session, settings)


@router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
def create(request: PropertyCreateRequest, session: Db, user: CurrentUser) -> object:
    return PropertyService(session).create(request, user)


@router.get("/mine", response_model=list[PropertySummaryResponse])
def mine(
    session: Db,
    user: CurrentUser,
    status_filter: Annotated[PropertyStatus | None, Query(alias="status")] = None,
) -> list[object]:
    return list(PropertyService(session).mine(user, status_filter))


@router.get("/{property_public_id}", response_model=PropertyResponse)
def details(
    property_public_id: str, session: Db, user: Annotated[User | None, Depends(optional_user)]
) -> object:
    return PropertyService(session).details(property_public_id, user)


@router.patch("/{property_public_id}", response_model=PropertyResponse)
def update(
    property_public_id: str, request: PropertyUpdateRequest, session: Db, user: CurrentUser
) -> object:
    return PropertyService(session).update(property_public_id, request, user)


@router.post("/{property_public_id}/submit", response_model=PropertyResponse)
def submit(property_public_id: str, session: Db, user: CurrentUser) -> object:
    return PropertyService(session).submit(property_public_id, user)


@router.delete("/{property_public_id}", response_model=PropertyResponse)
def archive(property_public_id: str, session: Db, user: CurrentUser) -> object:
    return PropertyService(session).archive(property_public_id, user)
