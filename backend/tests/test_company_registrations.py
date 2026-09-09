from fastapi.testclient import TestClient

from utils.cpf import build_cpf

PLATFORM_HEADERS = {"X-Platform-Key": "test-platform-key"}
VALID_CNPJ = "11222333000181"


def _registration_payload(**overrides):
    payload = {
        "legal_name": "Nova Empresa LTDA",
        "trade_name": "Nova Empresa",
        "document": VALID_CNPJ,
        "admin_name": "Admin Novo",
        "admin_email": "admin.novo@exemplo.com",
        "admin_cpf": build_cpf(424242424),
        "declared_store_count": 3,
    }
    payload.update(overrides)
    return payload


def test_public_registration_creates_pending(client: TestClient):
    response = client.post("/company-registrations/", json=_registration_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["document"] == VALID_CNPJ
    assert data["declared_store_count"] == 3


def test_registration_rejects_more_than_15_stores(client: TestClient):
    response = client.post(
        "/company-registrations/",
        json=_registration_payload(declared_store_count=16),
    )
    assert response.status_code == 422
    assert "15" in response.json()["detail"]


def test_list_registrations_requires_platform_key(client: TestClient):
    assert client.get("/company-registrations/").status_code == 401

    create = client.post("/company-registrations/", json=_registration_payload())
    assert create.status_code == 201

    listed = client.get("/company-registrations/", headers=PLATFORM_HEADERS)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1


def test_approve_provisions_company_and_admin(client: TestClient):
    create = client.post("/company-registrations/", json=_registration_payload())
    request_id = create.json()["id"]

    approve = client.post(
        f"/company-registrations/{request_id}/approve",
        headers=PLATFORM_HEADERS,
        json={"has_branches": False},
    )
    assert approve.status_code == 200
    body = approve.json()
    assert body["company_id"] > 0
    assert body["temporary_password"]
    assert body["admin_email"] == "admin.novo@exemplo.com"
    assert body["registration"]["status"] == "approved"

    login = client.post(
        "/auth/login",
        json={
            "company_document": VALID_CNPJ,
            "login": body["admin_email"],
            "password": body["temporary_password"],
        },
    )
    assert login.status_code == 200

    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["company"]["document"] == VALID_CNPJ
    assert me.json()["company"]["has_branches"] is False


def test_reject_registration(client: TestClient):
    create = client.post(
        "/company-registrations/",
        json=_registration_payload(document="34028316000103", admin_email="rej@exemplo.com"),
    )
    request_id = create.json()["id"]

    reject = client.post(
        f"/company-registrations/{request_id}/reject",
        headers=PLATFORM_HEADERS,
        json={"notes": "CNPJ inválido na consulta"},
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"
    assert reject.json()["notes"] == "CNPJ inválido na consulta"


def test_patch_company_me_toggles_has_branches(client: TestClient):
    me = client.get("/companies/me")
    assert me.status_code == 200
    assert me.json()["has_branches"] is False

    updated = client.patch("/companies/me", json={"has_branches": True})
    assert updated.status_code == 200
    assert updated.json()["has_branches"] is True

    auth_me = client.get("/auth/me")
    assert auth_me.json()["company"]["has_branches"] is True
