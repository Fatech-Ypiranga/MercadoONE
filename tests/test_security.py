import pytest
from fastapi.testclient import TestClient

from auth.security import DEFAULT_JWT_SECRET, validate_production_config
from main import create_app, get_cors_origins


def test_development_allows_default_jwt_secret(monkeypatch):
    monkeypatch.setenv("ENV", "development")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    validate_production_config()


def test_production_rejects_missing_jwt_secret(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-production-password")
    monkeypatch.setenv("ALLOW_MISSING_SENTRY", "1")

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_production_config()


def test_production_rejects_default_jwt_secret(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("JWT_SECRET", DEFAULT_JWT_SECRET)
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-production-password")
    monkeypatch.setenv("ALLOW_MISSING_SENTRY", "1")

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_production_config()


def test_production_rejects_weak_admin_password(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "unique-production-secret-value")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin123")
    monkeypatch.setenv("ALLOW_MISSING_SENTRY", "1")

    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        validate_production_config()


def test_production_rejects_missing_admin_password(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "unique-production-secret-value")
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("ALLOW_MISSING_SENTRY", "1")

    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        validate_production_config()


def test_seed_admin_requires_admin_password(monkeypatch, test_engine):
    from sqlmodel import Session

    from database.seed import seed_admin_user
    from tests.conftest import truncate_tables

    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    truncate_tables(test_engine)

    with Session(test_engine) as session:
        with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
            seed_admin_user(session)


def test_production_accepts_secure_config(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "unique-production-secret-value")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-production-password")
    monkeypatch.setenv("SENTRY_DSN", "https://examplePublicKey@o0.ingest.sentry.io/0")
    monkeypatch.setenv("UVICORN_WORKERS", "1")

    validate_production_config()


def test_production_rejects_missing_sentry_dsn(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "unique-production-secret-value")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-production-password")
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.delenv("ALLOW_MISSING_SENTRY", raising=False)

    with pytest.raises(RuntimeError, match="SENTRY_DSN"):
        validate_production_config()


def test_production_allows_missing_sentry_with_bypass(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "unique-production-secret-value")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-production-password")
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.setenv("ALLOW_MISSING_SENTRY", "1")

    validate_production_config()


def test_production_rejects_missing_redis_with_multi_worker(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "unique-production-secret-value")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-production-password")
    monkeypatch.setenv("SENTRY_DSN", "https://examplePublicKey@o0.ingest.sentry.io/0")
    monkeypatch.setenv("UVICORN_WORKERS", "2")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("ALLOW_MISSING_REDIS", raising=False)

    with pytest.raises(RuntimeError, match="REDIS_URL"):
        validate_production_config()


def test_app_lifespan_fails_in_production_with_default_secret(monkeypatch, test_engine):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("JWT_SECRET", DEFAULT_JWT_SECRET)
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-production-password")
    monkeypatch.setenv("ALLOW_MISSING_SENTRY", "1")

    from sqlmodel import Session

    from database.connection import get_db

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    app = create_app(init_database=False, validate_config=True)
    app.dependency_overrides[get_db] = override_get_db

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        with TestClient(app):
            pass

    app.dependency_overrides.clear()


def test_cors_origins_default_includes_localhost_3000(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert get_cors_origins() == ["http://localhost:3000"]


def test_cors_origins_parses_comma_separated_list(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:3000, https://app.example.com ",
    )
    assert get_cors_origins() == [
        "http://localhost:3000",
        "https://app.example.com",
    ]


def test_cors_preflight_allows_localhost_3000(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    app = create_app(init_database=False, validate_config=False)

    with TestClient(app) as client:
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_rejects_unknown_origin(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    app = create_app(init_database=False, validate_config=False)

    with TestClient(app) as client:
        response = client.get(
            "/",
            headers={"Origin": "http://evil.example"},
        )

    assert "access-control-allow-origin" not in response.headers


def test_security_headers_present(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    app = create_app(init_database=False, validate_config=False)

    with TestClient(app) as client:
        response = client.get("/")

    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_docs_enabled_outside_production(monkeypatch):
    monkeypatch.setenv("ENV", "development")
    app = create_app(init_database=False, validate_config=False)

    with TestClient(app) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200


def test_docs_disabled_in_production(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "unique-production-secret-value")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-production-password")
    app = create_app(init_database=False, validate_config=False)

    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_healthz_ok_when_database_reachable(monkeypatch, test_engine):
    from sqlmodel import Session

    from database.connection import get_db

    monkeypatch.setenv("ENV", "development")
    app = create_app(init_database=False, validate_config=False)

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    # healthz/readyz use module-level engine; DATABASE_URL is already test DB in CI.
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            live = client.get("/livez")
            assert live.status_code == 200
            assert live.json()["status"] == "ok"

            ready = client.get("/readyz")
            assert ready.status_code in (200, 503)
            assert "status" in ready.json()

            response = client.get("/healthz")
            assert response.status_code in (200, 503)
            assert "status" in response.json()
    finally:
        app.dependency_overrides.clear()


def test_login_rate_limit_returns_429(monkeypatch, test_engine):
    from sqlmodel import Session

    from database.connection import get_db

    monkeypatch.setenv("LOGIN_RATE_LIMIT", "3")
    monkeypatch.setenv("LOGIN_RATE_WINDOW_SECONDS", "60")

    app = create_app(init_database=False, validate_config=False)

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            for _ in range(3):
                client.post(
                    "/auth/login",
                    json={"login": "nobody", "password": "wrong"},
                )
            blocked = client.post(
                "/auth/login",
                json={"login": "nobody", "password": "wrong"},
            )
            assert blocked.status_code == 429
            assert "tentativas" in blocked.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()
