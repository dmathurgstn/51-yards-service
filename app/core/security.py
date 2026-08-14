from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Literal
from uuid import uuid4

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import Settings
from app.core.exceptions import ApplicationError

password_hasher = PasswordHash.recommended()
TokenType = Literal["access", "refresh"]


@dataclass(frozen=True)
class TokenClaims:
    subject: str
    jti: str
    token_type: TokenType
    expires_at: datetime


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def hash_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def create_token(
    subject: str, token_type: TokenType, settings: Settings
) -> tuple[str, TokenClaims]:
    now = datetime.now(UTC)
    lifetime = (
        timedelta(minutes=settings.access_token_expire_minutes)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_expire_days)
    )
    claims = TokenClaims(subject, str(uuid4()), token_type, now + lifetime)
    payload = {
        "sub": subject,
        "jti": claims.jti,
        "type": token_type,
        "iat": now,
        "exp": claims.expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm), claims


def decode_token(token: str, expected_type: TokenType, settings: Settings) -> TokenClaims:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != expected_type:
            raise ApplicationError(
                "AUTH_TOKEN_INVALID", "The authentication token is invalid.", status_code=401
            )
        return TokenClaims(
            str(payload["sub"]),
            str(payload["jti"]),
            expected_type,
            datetime.fromtimestamp(int(payload["exp"]), UTC),
        )
    except ExpiredSignatureError as exc:
        raise ApplicationError(
            "AUTH_TOKEN_EXPIRED", "The authentication token has expired.", status_code=401
        ) from exc
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise ApplicationError(
            "AUTH_TOKEN_INVALID", "The authentication token is invalid.", status_code=401
        ) from exc
