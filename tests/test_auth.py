import os

from fastapi.testclient import TestClient
from sqlmodel import Session

from database.connection import get_db
from database.seed import seed_admin_user
from main import create_app
from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME, create_test_user
from utils.enums import UserProfile


def test_login_with_username(client: TestClient):
    response = client.post(
        "/auth/login", json={"login": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_with_email(test_engine):
    with Session(test_engine) as session:
        seed_admin_user(session)

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    app = create_app(init_database=False)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        response = test_client.post(
            "/auth/login",
            json={
                "login": os.getenv("ADMIN_EMAIL", "admin@pyerp.local"),
                "password": ADMIN_PASSWORD,
            },
        )
        assert response.status_code == 200

    app.dependency_overrides.clear()


def test_login_invalid_credentials(client: TestClient):
    response = client.post("/auth/login", json={"login": ADMIN_USERNAME, "password": "wrong"})
    assert response.status_code == 401


def test_inactive_user_cannot_login(test_engine):
    with Session(test_engine) as session:
        seed_admin_user(session)
        user = create_test_user(
            session,
            full_name="Inativo",
            cpf="44444444444",
            email="inativo@test.local",
            username="inativo",
            password="inativo1",
            profile=UserProfile.COLABORADOR,
        )
        user.is_active = False
        session.add(user)
        session.commit()

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    app = create_app(init_database=False)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        response = test_client.post(
            "/auth/login", json={"login": "inativo", "password": "inativo1"}
        )
        assert response.status_code == 401

    app.dependency_overrides.clear()


def test_auth_me_returns_user(client: TestClient):
    response = client.get("/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == ADMIN_USERNAME
    assert data["profile"] == "admin"
    assert "password_hash" not in data


def test_unauthenticated_request_returns_401(test_engine):
    def override_get_db():
        with Session(test_engine) as session:
            yield session

    app = create_app(init_database=False)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        response = test_client.get("/products/")
        assert response.status_code == 401

    app.dependency_overrides.clear()


def test_change_password(client: TestClient):
    response = client.post(
        "/auth/change-password",
        json={"current_password": ADMIN_PASSWORD, "new_password": "newadmin1"},
    )
    assert response.status_code == 204

    relogin = client.post("/auth/login", json={"login": ADMIN_USERNAME, "password": "newadmin1"})
    assert relogin.status_code == 200

    client.post(
        "/auth/change-password",
        json={"current_password": "newadmin1", "new_password": ADMIN_PASSWORD},
    )


def test_change_password_wrong_current_returns_422(client: TestClient):
    response = client.post(
        "/auth/change-password",
        json={"current_password": "wrong-password", "new_password": "newadmin2"},
    )
    assert response.status_code == 422
    assert "incorrect" in response.json()["detail"].lower()
