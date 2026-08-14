from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import ApplicationError
from app.core.security import decode_token
from app.db.session import get_db_session
from app.models.user import User
from app.repositories.user_repository import UserRepository

bearer = HTTPBearer(auto_error=False)


def require_authenticated_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApplicationError("AUTH_TOKEN_INVALID", "Authentication is required.", status_code=401)
    claims = decode_token(credentials.credentials, "access", settings)
    user = UserRepository(session).by_public_id(claims.subject)
    if user is None:
        raise ApplicationError(
            "AUTH_TOKEN_INVALID", "The authentication token is invalid.", status_code=401
        )
    return user


def require_active_user(user: Annotated[User, Depends(require_authenticated_user)]) -> User:
    if not user.is_active:
        raise ApplicationError(
            "AUTH_ACCOUNT_INACTIVE", "This account is inactive.", status_code=403
        )
    return user


def require_role(code: str) -> Callable[[User], User]:
    def dependency(user: Annotated[User, Depends(require_active_user)]) -> User:
        if code not in {role.code for role in user.roles}:
            raise ApplicationError(
                "AUTH_FORBIDDEN",
                "You do not have permission to perform this action.",
                status_code=403,
            )
        return user

    return dependency
