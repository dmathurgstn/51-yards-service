from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import ApplicationError
from app.core.security import create_token, decode_token, hash_password, hash_token, verify_password
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import RoleRepository, UserRepository
from app.schemas.auth import LoginRequest, RegistrationRequest, TokenResponse
from app.schemas.user import UserResponse


def user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(
        {
            "public_id": user.public_id,
            "full_name": user.full_name,
            "email": user.email,
            "mobile_number": user.mobile_number,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "roles": [role.code for role in user.roles],
        }
    )


class AuthService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.tokens = RefreshTokenRepository(session)

    def register(self, request: RegistrationRequest) -> UserResponse:
        email = str(request.email).strip().lower()
        if self.users.by_email(email):
            raise ApplicationError(
                "USER_EMAIL_EXISTS", "An account with this email already exists.", status_code=409
            )
        if request.mobile_number and self.users.by_mobile(request.mobile_number):
            raise ApplicationError(
                "USER_MOBILE_EXISTS",
                "An account with this mobile number already exists.",
                status_code=409,
            )
        role = self.roles.by_code(request.user_type)
        if role is None or not role.is_active:
            raise ApplicationError(
                "ROLE_INVALID", "The selected user type is unavailable.", status_code=400
            )
        user = User(
            full_name=request.full_name,
            email=email,
            mobile_number=request.mobile_number,
            password_hash=hash_password(request.password),
            roles=[role],
        )
        self.users.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user_response(user)

    def login(self, request: LoginRequest) -> TokenResponse:
        user = self.users.by_email(str(request.email).strip().lower())
        if user is None or not verify_password(request.password, user.password_hash):
            raise ApplicationError(
                "AUTH_INVALID_CREDENTIALS", "Invalid email or password.", status_code=401
            )
        if not user.is_active:
            raise ApplicationError(
                "AUTH_ACCOUNT_INACTIVE", "This account is inactive.", status_code=403
            )
        user.last_login_at = datetime.now(UTC)
        response = self._issue_session(user)
        self.session.commit()
        return response

    def refresh(self, raw_token: str) -> TokenResponse:
        claims = decode_token(raw_token, "refresh", self.settings)
        stored = self.tokens.by_jti(claims.jti)
        if (
            stored is None
            or stored.revoked_at is not None
            or stored.token_hash != hash_token(raw_token)
        ):
            raise ApplicationError(
                "AUTH_REFRESH_REVOKED", "The refresh session is no longer valid.", status_code=401
            )
        user = stored.user
        if not user.is_active:
            raise ApplicationError(
                "AUTH_ACCOUNT_INACTIVE", "This account is inactive.", status_code=403
            )
        now = datetime.now(UTC)
        stored.revoked_at = now
        stored.last_used_at = now
        response = self._issue_session(user)
        self.session.commit()
        return response

    def logout(self, raw_token: str) -> None:
        try:
            claims = decode_token(raw_token, "refresh", self.settings)
        except ApplicationError:
            return
        stored = self.tokens.by_jti(claims.jti)
        if stored and stored.token_hash == hash_token(raw_token) and stored.revoked_at is None:
            stored.revoked_at = datetime.now(UTC)
            self.session.commit()

    def _issue_session(self, user: User) -> TokenResponse:
        access, _ = create_token(user.public_id, "access", self.settings)
        refresh, claims = create_token(user.public_id, "refresh", self.settings)
        self.tokens.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(refresh),
                jti=claims.jti,
                expires_at=claims.expires_at,
            )
        )
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=self.settings.access_token_expire_minutes * 60,
            user=user_response(user),
        )
