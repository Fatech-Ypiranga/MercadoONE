"""Regression tests for QA/security audit fixes."""

from decimal import Decimal

from fastapi.testclient import TestClient

from database.seed import SEED_COMPANY_DOCUMENT
from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME
from utils.cpf import build_cpf


def _login(login: str, password: str) -> dict:
    return {
        "login": login,
        "password": password,
        "company_document": SEED_COMPANY_DOCUMENT,
    }


def test_pdv_authorization_token_rejected_as_bearer(client: TestClient, operador_client: TestClient):
    supervisor = client.post(
        "/users/",
        json={
            "full_name": "Supervisor Token Confusion",
            "cpf": build_cpf(801),
            "email": "sup-token@test.local",
            "username": "suptoken",
            "password": "senha123",
            "profile": "supervisor",
            "is_active": True,
        },
    ).json()
    pin = client.post(f"/users/{supervisor['id']}/pdv-pin").json()["pdv_pin"]

    authorize = operador_client.post(
        "/auth/pdv-authorize",
        json={
            "pdv_id": supervisor["pdv_id"],
            "pin": pin,
            "actions": ["discount", "cancel"],
        },
    )
    assert authorize.status_code == 200
    pdv_token = authorize.json()["authorization_token"]

    hijack = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {pdv_token}"},
    )
    assert hijack.status_code == 401


def test_duplicate_product_lines_cannot_oversell(client: TestClient, stocked_product):
    product_id = stocked_product["id"]
    # stocked_product starts with 20 units
    response = client.post(
        "/sales/",
        json={
            "items": [
                {"product_id": product_id, "quantity": 12},
                {"product_id": product_id, "quantity": 12},
            ],
        },
    )
    assert response.status_code == 409


def test_negative_stock_quantity_rejected(client: TestClient, product):
    response = client.post(
        "/stock/move",
        json={
            "product_id": product["id"],
            "quantity": "-5",
            "type": "S",
            "reason": "ajuste",
        },
    )
    assert response.status_code == 422


def test_change_password_invalidates_existing_token(client: TestClient):
    login = client.post("/auth/login", json=_login(ADMIN_USERNAME, ADMIN_PASSWORD))
    assert login.status_code == 200
    old_token = login.json()["access_token"]

    change = client.post(
        "/auth/change-password",
        json={"current_password": ADMIN_PASSWORD, "new_password": "newadmin1"},
        headers={"Authorization": f"Bearer {old_token}"},
    )
    assert change.status_code == 204

    stale = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {old_token}"},
    )
    assert stale.status_code == 401

    relogin = client.post("/auth/login", json=_login(ADMIN_USERNAME, "newadmin1"))
    assert relogin.status_code == 200
    new_token = relogin.json()["access_token"]
    restore = client.post(
        "/auth/change-password",
        json={"current_password": "newadmin1", "new_password": ADMIN_PASSWORD},
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert restore.status_code == 204
    # Keep shared client fixture usable for subsequent tests in the same module.
    final = client.post("/auth/login", json=_login(ADMIN_USERNAME, ADMIN_PASSWORD))
    assert final.status_code == 200
    client.headers["Authorization"] = f"Bearer {final.json()['access_token']}"


def test_cancelled_sales_excluded_from_average_ticket(client: TestClient, stocked_product):
    product_id = stocked_product["id"]
    sale = client.post(
        "/sales/",
        json={"items": [{"product_id": product_id, "quantity": 2}]},
    ).json()
    client.post(f"/sales/{sale['id']}/cancel")

    ticket = client.get("/reports/average-ticket")
    assert ticket.status_code == 200
    assert Decimal(str(ticket.json()["average_ticket"])) == Decimal("0")


def test_pdv_login_rate_limited(monkeypatch, test_engine):
    from sqlmodel import Session

    from database.connection import get_db
    from main import create_app

    monkeypatch.setenv("LOGIN_RATE_LIMIT", "3")
    monkeypatch.setenv("LOGIN_RATE_WINDOW_SECONDS", "60")

    app = create_app(init_database=False, validate_config=False)

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as tc:
            for _ in range(3):
                tc.post(
                    "/auth/pdv-login",
                    json={
                        "company_document": SEED_COMPANY_DOCUMENT,
                        "pdv_id": "000001",
                        "password": "wrong",
                    },
                )
            blocked = tc.post(
                "/auth/pdv-login",
                json={
                    "company_document": SEED_COMPANY_DOCUMENT,
                    "pdv_id": "000001",
                    "password": "wrong",
                },
            )
            assert blocked.status_code == 429
    finally:
        app.dependency_overrides.clear()
