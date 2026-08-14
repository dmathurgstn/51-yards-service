import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("YARDS_APPLICATION_NAME", "51 Yards API")
os.environ.setdefault(
    "YARDS_DATABASE_URL", "mysql+pymysql://test:test@localhost:3306/fifty_one_yards"
)
os.environ.setdefault("YARDS_ENVIRONMENT", "testing")
os.environ.setdefault("YARDS_JWT_SECRET_KEY", "test-secret-key-with-at-least-32-characters")

from app.api.v1.endpoints.health import get_health_service  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.main import create_application  # noqa: E402
from app.services.health_service import HealthService  # noqa: E402


@pytest.fixture
def settings() -> Settings:
    return Settings(
        application_name="51 Yards API",
        application_version="1.0.0",
        environment="testing",
        debug=False,
        api_v1_prefix="/api/v1",
        frontend_origins=["http://localhost:4200"],
        database_url="mysql+pymysql://test:test@localhost:3306/fifty_one_yards",
        log_level="WARNING",
        jwt_secret_key="test-secret-key-with-at-least-32-characters",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    application = create_application(settings)
    application.dependency_overrides[get_health_service] = lambda: HealthService(
        settings, lambda: True
    )
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client
