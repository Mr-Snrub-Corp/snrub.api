# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI REST API backend using Python 3.11+, SQLModel ORM, PostgreSQL (psycopg3), and UV package manager. Runs in Docker for local development alongside a Vue.js client (`../snrub.client`), PostgreSQL, and Mailhog.

## Commands

### Development (Docker)
```bash
docker-compose up -d --build          # Build and start all services
docker compose logs -f api            # View API logs
docker compose down                   # Stop services
```

### Testing
Docker must be running for integration tests (they hit the real test database).
```bash
APP_ENV=test uv run pytest                          # All tests
APP_ENV=test uv run pytest tests/integration        # Integration tests only
APP_ENV=test uv run pytest tests/unit               # Unit tests only
APP_ENV=test uv run pytest tests/integration/test_auth_login.py  # Single file
APP_ENV=test uv run pytest -v                       # Verbose output
```

### Linting (Ruff)
```bash
ruff check .            # Lint
ruff check . --fix      # Auto-fix
ruff format .           # Format
```
Line length: 120. Target: py311. Ignores B008 (function call in default args, needed for FastAPI `Depends()`). Excludes `migrations/`, `lib/`, `venv/`.

### Database Migrations (Alembic)
```bash
docker compose exec api alembic revision --autogenerate -m "Description"
docker compose exec api alembic upgrade head
```

## Architecture

**Layered pattern:** Routes → Controllers → CRUDBase/Services → Models → Database

- **`app/routes/`** — FastAPI routers defining HTTP endpoints. All prefixed with `/api`. Auth is split into `auth/local.py` (email/password) and `auth/google.py` (OAuth).
- **`app/controllers/`** — Business logic called by routes. `auth/local.py` handles login/password-reset flows; `user.py` handles user CRUD orchestration.
- **`app/db/crud_base.py`** — Generic `CRUDBase[ModelType]` class providing reusable CRUD operations. Uses `"uid"` as default primary key field name.
- **`app/models/`** — SQLModel classes (combined SQLAlchemy table + Pydantic validation). Separate Pydantic models for API request/response schemas.
- **`app/services/`** — Side-effect services: `email.py` (FastAPI-Mail), `image_processing.py` (Pillow — resizes to 160x160 8-bit palette PNG).
- **`app/security/`** — JWT token handling (`jwt.py`), bearer auth dependency (`auth_bearer.py`), role-based authorization (`authorization.py`), Google OAuth client (`oauth_client.py`).
- **`app/core/config.py`** — Pydantic `Settings` class. Loads env from `.env.{APP_ENV}` (defaults to `.env.development`). Set `APP_ENV=test` for test config.

## Key Patterns

- **Dependency injection:** `Depends(get_session)` for DB sessions, `Depends(JWTBearer())` for auth, `Depends(verify_admin_access)` for role checks.
- **User roles:** `UserRole` enum — VIEWER, CREATOR, ADMIN, SUPER_ADMIN. Admin endpoints require ADMIN or SUPER_ADMIN.
- **User status:** `UserStatus` enum — ACTIVE, INACTIVE, DECEASED, SUSPENDED.
- **Password hashing:** bcrypt via passlib (`pwd_context` in `controllers/user.py`).
- **Test fixtures:** Integration tests use `mimesis` for fake data. Fixtures in `tests/integration/conftest.py` provide `authenticated_user`, `admin_user`, `auth_headers`, `admin_auth_headers`, etc. Sessions roll back after each test.
- **API docs:** Scalar UI at `http://localhost:8000/docs` (Swagger UI disabled).

## Environment

Copy `.env.example` to `.env.development` and `.env.test`. Key vars: `POSTGRES_*`, `JWT_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `MAIL_*`. The `APP_ENV` variable selects which `.env.*` file to load.
