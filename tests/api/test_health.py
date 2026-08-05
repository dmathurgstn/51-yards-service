from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.endpoints.health import get_health_service
from app.core.config import Settings
from app.main import create_application
from app.services.health_service import HealthService


def test_application_root_and_openapi(client: TestClient) -> None:
    root = client.get("/")
    assert root.status_code == 200
    assert root.json() == {
        "service": "51 Yards API",
        "documentation": "/docs",
        "version": "1.0.0",
    }
    assert client.get("/openapi.json").status_code == 200


def test_liveness_does_not_check_database(settings: Settings) -> None:
    calls = 0

    def checker() -> bool:
        nonlocal calls
        calls += 1
        return False

    application = create_application(settings)
    application.dependency_overrides[get_health_service] = lambda: HealthService(settings, checker)
    with TestClient(application) as test_client:
        response = test_client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert calls == 0


def test_readiness_connected(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"


def test_readiness_disconnected_and_summary_degraded(settings: Settings) -> None:
    application = create_application(settings)
    application.dependency_overrides[get_health_service] = lambda: HealthService(
        settings, lambda: False
    )
    with TestClient(application) as test_client:
        readiness = test_client.get("/api/v1/health/ready")
        summary = test_client.get("/api/v1/health")
    assert readiness.status_code == 503
    assert readiness.json() == {
        "status": "not_ready",
        "service": "51 Yards API",
        "database": "disconnected",
    }
    assert summary.status_code == 200
    assert summary.json()["status"] == "degraded"
    assert datetime.fromisoformat(summary.json()["timestamp"]).tzinfo is not None


def test_request_id_is_preserved_or_generated(client: TestClient) -> None:
    request_id = str(uuid4())
    preserved = client.get("/api/v1/health/live", headers={"X-Request-ID": request_id})
    generated = client.get("/api/v1/health/live", headers={"X-Request-ID": "not-a-uuid"})
    assert preserved.headers["X-Request-ID"] == request_id
    assert generated.headers["X-Request-ID"] != "not-a-uuid"


def test_cors_allowed_disallowed_and_preflight(client: TestClient) -> None:
    allowed = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:4200",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Request-ID",
        },
    )
    disallowed = client.get(
        "/api/v1/health/live", headers={"Origin": "https://not-allowed.example"}
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:4200"
    assert "access-control-allow-origin" not in disallowed.headers
