import os

from fastapi.testclient import TestClient
from sqlmodel import Session

from database.connection import get_db
from database.seed import SEED_COMPANY_DOCUMENT, seed_admin_user
from main import create_app
from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME, create_test_user
from utils.cpf import build_cpf
from utils.enums import UserProfile


def _login(login: str, password: str) -> dict:
    return {
        "login": login,
        "password": password,
        "company_document": SEED_COMPANY_DOCUMENT,
    }


def test_login_with_username(client: TestClient):
    response = client.post("/auth/login", json=_login(ADMIN_USERNAME, ADMIN_PASSWORD))
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_requires_company_document(client: TestClient):
    response = client.post(
        "/auth/login", json={"login": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 422


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
            json=_login(os.getenv("ADMIN_EMAIL", "admin@pyerp.local"), ADMIN_PASSWORD),
        )
        assert response.status_code == 200

    app.dependency_overrides.clear()


def test_login_invalid_credentials(client: TestClient):
    response = client.post("/auth/login", json=_login(ADMIN_USERNAME, "wrong"))
    assert response.status_code == 401


def test_inactive_user_cannot_login(test_engine):
    with Session(test_engine) as session:
        seed_admin_user(session)
        user = create_test_user(
            session,
            full_name="Inativo",
            cpf=build_cpf(301),
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
        response = test_client.post("/auth/login", json=_login("inativo", "inativo1"))
        assert response.status_code == 401

    app.dependency_overrides.clear()


def test_auth_me_returns_user(client: TestClient):
    response = client.get("/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == ADMIN_USERNAME
    assert data["profile"] == "admin"
    assert "password_hash" not in data
    assert data["pdv_id"] is not None


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

    relogin = client.post("/auth/login", json=_login(ADMIN_USERNAME, "newadmin1"))
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


def test_pdv_login_and_authorize_discount(client: TestClient, operador_client: TestClient):
    supervisor = client.post(
        "/users/",
        json={
            "full_name": "Supervisor PDV",
            "cpf": build_cpf(302),
            "email": "suppdv@test.local",
            "username": "suppdv",
            "password": "senha123",
            "profile": "supervisor",
            "is_active": True,
        },
    ).json()
    pin = client.post(f"/users/{supervisor['id']}/pdv-pin").json()["pdv_pin"]

    operator = client.get("/users/", params={"q": "operador"}).json()["items"]
    operator_user = next(item for item in operator if item["username"] == "operador")

    pdv_login = client.post(
        "/auth/pdv-login",
        json={
            "company_document": SEED_COMPANY_DOCUMENT,
            "pdv_id": operator_user["pdv_id"],
            "password": "oper1234",
        },
    )
    assert pdv_login.status_code == 200

    authorize = operador_client.post(
        "/auth/pdv-authorize",
        json={
            "pdv_id": supervisor["pdv_id"],
            "pin": pin,
            "actions": ["discount", "cancel"],
        },
    )
    assert authorize.status_code == 200
    assert "discount" in authorize.json()["actions"]
    assert authorize.json()["authorization_token"]
