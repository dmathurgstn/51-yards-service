from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import create_application
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User


@pytest.fixture
def auth_client(settings: Settings) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        session.add_all(
            Role(code=code, name=code) for code in ("USER", "OWNER", "AGENT", "BUILDER", "ADMIN")
        )
        session.commit()

    def database() -> Iterator[Session]:
        with factory() as session:
            yield session

    app = create_application(settings)
    app.dependency_overrides[get_db_session] = database
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, factory


def registration(
    email: str = "buyer@example.com", mobile: str = "9876543210", role: str = "USER"
) -> dict[str, str]:
    return {
        "fullName": "Test Buyer",
        "email": email,
        "mobileNumber": mobile,
        "password": "secure-pass-123",
        "confirmPassword": "secure-pass-123",
        "userType": role,
    }


def test_registration_validates_duplicates_roles_and_hashes_password(
    auth_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, factory = auth_client
    response = client.post("/api/v1/auth/register", json=registration())
    assert response.status_code == 201
    assert response.json()["roles"] == ["USER"]
    assert "password" not in response.text
    assert (
        client.post("/api/v1/auth/register", json=registration()).json()["error"]["code"]
        == "USER_EMAIL_EXISTS"
    )
    assert (
        client.post("/api/v1/auth/register", json=registration("other@example.com")).json()[
            "error"
        ]["code"]
        == "USER_MOBILE_EXISTS"
    )
    assert (
        client.post(
            "/api/v1/auth/register", json=registration("admin@example.com", "9876543211", "ADMIN")
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/auth/register",
            json={
                **registration("weak@example.com", "9876543212"),
                "password": "short",
                "confirmPassword": "short",
            },
        ).status_code
        == 422
    )
    with factory() as session:
        user = session.scalar(select(User).where(User.email == "buyer@example.com"))
        assert (
            user
            and user.password_hash != "secure-pass-123"
            and user.password_hash.startswith("$argon2")
        )


def test_login_me_refresh_rotation_and_logout(
    auth_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, factory = auth_client
    client.post("/api/v1/auth/register", json=registration())
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "missing@example.com", "password": "wrong"}
        ).status_code
        == 401
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": "buyer@example.com", "password": "secure-pass-123"}
    )
    assert login.status_code == 200
    tokens = login.json()
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['accessToken']}"})
    assert me.status_code == 200 and me.json()["email"] == "buyer@example.com"
    assert "password" not in me.text
    rotated = client.post("/api/v1/auth/refresh", json={"refreshToken": tokens["refreshToken"]})
    assert rotated.status_code == 200 and rotated.json()["refreshToken"] != tokens["refreshToken"]
    assert (
        client.post("/api/v1/auth/refresh", json={"refreshToken": tokens["refreshToken"]}).json()[
            "error"
        ]["code"]
        == "AUTH_REFRESH_REVOKED"
    )
    new_refresh = rotated.json()["refreshToken"]
    assert client.post("/api/v1/auth/logout", json={"refreshToken": new_refresh}).status_code == 200
    assert client.post("/api/v1/auth/logout", json={"refreshToken": new_refresh}).status_code == 200
    with factory() as session:
        assert len(session.scalars(select(RefreshToken)).all()) == 2


def test_access_token_rejections_and_inactive_user(
    auth_client: tuple[TestClient, sessionmaker[Session]], settings: Settings
) -> None:
    client, factory = auth_client
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": "Bearer malformed"}).status_code
        == 401
    )
    payload = {
        "sub": "unknown",
        "jti": "expired",
        "type": "access",
        "iat": datetime.now(UTC) - timedelta(hours=2),
        "exp": datetime.now(UTC) - timedelta(hours=1),
    }
    expired = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}).json()[
            "error"
        ]["code"]
        == "AUTH_TOKEN_EXPIRED"
    )
    client.post("/api/v1/auth/register", json=registration())
    with factory() as session:
        user = session.scalar(select(User).where(User.email == "buyer@example.com"))
        assert user
        user.is_active = False
        session.commit()
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "buyer@example.com", "password": "secure-pass-123"}
        ).json()["error"]["code"]
        == "AUTH_ACCOUNT_INACTIVE"
    )
