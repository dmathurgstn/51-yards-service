# 51 Yards Services

FastAPI foundation for 51 Yards. Sprint 4 provides configuration, logging, CORS, correlation IDs, a stable error contract, SQLAlchemy/MySQL connectivity, Alembic, and health APIs. It intentionally contains no business tables, authentication, property APIs, uploads, or AI features.

## Prerequisites and setup

- Python 3.12 (developed with 3.12.7)
- MySQL 8

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

For CMD, activate with `.venv\Scripts\activate.bat`. Replace the placeholder database password in the untracked `.env` file.

Create the UTF-8 database and a dedicated local application user using an administrator account:

```sql
CREATE DATABASE fifty_one_yards
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER 'yards_app'@'localhost'
IDENTIFIED BY 'replace-with-a-strong-local-password';
GRANT ALL PRIVILEGES ON fifty_one_yards.* TO 'yards_app'@'localhost';
FLUSH PRIVILEGES;
```

Do not commit the password or use `root` as the application identity.

## Run and inspect

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host localhost --port 8000
```

- Root: `http://localhost:8000/`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI: `http://localhost:8000/openapi.json`
- Combined diagnostic health: `GET /api/v1/health`
- Process liveness: `GET /api/v1/health/live`
- Database readiness: `GET /api/v1/health/ready`

Liveness does not query MySQL. Readiness returns 503 when `SELECT 1` fails. Combined health remains 200 with `status: degraded`, making it suitable for the internal Angular status page.

## Quality and migrations

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy app
python -m pytest
python -m pytest -m unit
python -m pytest -m integration
python -m pytest --cov=app --cov-report=term-missing
alembic current
alembic heads
```

Alembic reads the database URL from typed settings; it is not stored in `alembic.ini`. Sprint 4 deliberately has no empty baseline revision and creates no tables. Future schema changes should add meaningful revisions rather than calling `Base.metadata.create_all()`.

## Architecture and configuration

`app/api` owns versioned, thin HTTP handlers; `app/services` owns health orchestration; `app/db` owns the synchronous SQLAlchemy 2/PyMySQL engine, per-request sessions, base mixins, and connectivity check; `app/core` owns typed Pydantic settings, logging, middleware, and exception handling; `app/schemas` owns API contracts; `tests` mirrors those areas; and `alembic` is reserved for migrations.

All configuration is loaded once from `YARDS_*` environment variables (and `.env`) through `app.core.config.Settings`. The prefix prevents collisions with generic operating-system variables. `.env.example` is safe to commit; `.env` is ignored.

Logging uses the standard library with timestamp, level, logger, message, and request ID context. SQL statements and database credentials are not logged by default. The `X-Request-ID` middleware accepts a bounded valid incoming UUID or creates one, exposes it to request state/logs, and returns it in the response. Errors use:

```json
{"error":{"code":"INTERNAL_SERVER_ERROR","message":"An unexpected error occurred.","details":null,"requestId":"uuid"}}
```

CORS allows the configured origins (locally `http://localhost:4200`), required GET/OPTIONS traffic and headers, exposes `X-Request-ID`, and does not enable credentials. Separate Angular and API development origins require this browser permission.

The reusable timestamp mixin uses UTC-aware timestamps. Entity identifier strategy remains intentionally model-specific; internal relational IDs may use integers while public identifiers may use UUIDs.

## Security and deferred scope

Never expose `.env`, database URLs, authorization headers, tracebacks, or personal data. Use least-privilege database credentials and production-specific origins/settings. Property APIs, uploads, messaging, jobs, caching, payments, cloud deployment, and AI remain deferred.

## Sprint 5 authentication

Authentication uses `users`, `roles`, `user_roles`, and `refresh_tokens`. Passwords are Argon2 hashes. HS256 access JWTs last 15 minutes by default; refresh JWTs last seven days, are stored only as SHA-256 hashes, rotate on refresh, and are revoked by logout. Configure `YARDS_JWT_SECRET_KEY` with a random value of at least 32 characters.

```powershell
python -m alembic upgrade head
python -m app.utilities.seed_roles
$env:YARDS_ADMIN_EMAIL="admin@example.test"
$env:YARDS_ADMIN_PASSWORD="choose-a-local-password"
python -m app.utilities.create_admin
```

No admin credential is committed. The camelCase JSON endpoints are `POST /api/v1/auth/register`, `/login`, `/refresh`, `/logout`, and `GET /api/v1/auth/me`. Public `ADMIN` registration is rejected. Current limitations include no email/mobile verification, password reset, MFA, OAuth, access-token denylist, or HttpOnly refresh cookie.
