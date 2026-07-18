from decimal import Decimal

from fastapi.testclient import TestClient

from utils.cpf import build_cpf


def test_operador_cannot_create_user(operador_client: TestClient):
    response = operador_client.post(
        "/users/",
        json={
            "full_name": "Hack",
            "cpf": build_cpf(401),
            "email": "hack@test.local",
            "username": "hacker",
            "password": "hack1234",
            "profile": "admin",
            "is_active": True,
        },
    )
    assert response.status_code == 403


def test_operador_cannot_cancel_sale(operador_client: TestClient, stocked_product: dict):
    product_id = stocked_product["id"]
    sale = operador_client.post(
        "/sales/",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
    ).json()

    response = operador_client.post(f"/sales/{sale['id']}/cancel")
    assert response.status_code == 401


def test_operador_cannot_apply_discount(operador_client: TestClient, stocked_product: dict):
    product_id = stocked_product["id"]
    response = operador_client.post(
        "/sales/",
        json={
            "items": [{"product_id": product_id, "quantity": 1}],
            "discount_amount": "5.00",
        },
    )
    assert response.status_code == 401


def test_operador_cannot_move_stock(operador_client: TestClient, product: dict):
    response = operador_client.post(
        "/stock/move",
        json={
            "product_id": product["id"],
            "quantity": "5",
            "type": "E",
            "reason": "compra",
        },
    )
    assert response.status_code == 403


def test_conferente_can_move_stock(conferente_client: TestClient, product: dict):
    response = conferente_client.post(
        "/stock/move",
        json={
            "product_id": product["id"],
            "quantity": "5",
            "type": "E",
            "reason": "compra",
        },
    )
    assert response.status_code == 201


def test_colaborador_cannot_create_product(colaborador_client: TestClient, category: dict):
    response = colaborador_client.post(
        "/products/",
        json={
            "name": "Bloqueado",
            "sku": "BLK-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": category["id"],
        },
    )
    assert response.status_code == 403


def test_colaborador_can_list_products(colaborador_client: TestClient):
    response = colaborador_client.get("/products/")
    assert response.status_code == 200


def test_sale_user_id_from_token(client: TestClient, stocked_product: dict, admin_token: str):
    from jose import jwt

    from auth.security import JWT_ALGORITHM, JWT_SECRET

    payload = jwt.decode(admin_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    admin_id = int(payload["sub"])

    product_id = stocked_product["id"]
    response = client.post(
        "/sales/",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
    )
    assert response.status_code == 201
    assert response.json()["user_id"] == admin_id


def test_operador_processes_sale(operador_client: TestClient, stocked_product: dict):
    product_id = stocked_product["id"]
    response = operador_client.post(
        "/sales/",
        json={"items": [{"product_id": product_id, "quantity": 2}]},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "Concluida"

    balance = operador_client.get(f"/stock/product/{product_id}/balance")
    assert Decimal(str(balance.json()["current_balance"])) == Decimal("18")


def test_gerente_can_cancel_sale(gerente_client: TestClient, stocked_product: dict):
    product_id = stocked_product["id"]
    sale = gerente_client.post(
        "/sales/",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
    ).json()

    response = gerente_client.post(f"/sales/{sale['id']}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "Cancelada"


def test_gerente_can_apply_discount(gerente_client: TestClient, stocked_product: dict):
    product_id = stocked_product["id"]
    response = gerente_client.post(
        "/sales/",
        json={
            "items": [{"product_id": product_id, "quantity": 1}],
            "discount_amount": "10.00",
        },
    )
    assert response.status_code == 201
    assert response.json()["discount_amount"] == "10.00"
    assert response.json()["total_amount"] == "40.00"


def test_gerente_cannot_create_user(gerente_client: TestClient):
    response = gerente_client.post(
        "/users/",
        json={
            "full_name": "Hack Gerente",
            "cpf": build_cpf(402),
            "email": "hackger@test.local",
            "username": "hackger",
            "password": "hack1234",
            "profile": "operador",
            "is_active": True,
        },
    )
    assert response.status_code == 403


def test_supervisor_can_cancel_sale(supervisor_client: TestClient, stocked_product: dict):
    product_id = stocked_product["id"]
    sale = supervisor_client.post(
        "/sales/",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
    ).json()

    response = supervisor_client.post(f"/sales/{sale['id']}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "Cancelada"


def test_supervisor_can_move_stock(supervisor_client: TestClient, product: dict):
    response = supervisor_client.post(
        "/stock/move",
        json={
            "product_id": product["id"],
            "quantity": "3",
            "type": "E",
            "reason": "compra",
        },
    )
    assert response.status_code == 201


def test_supervisor_cannot_confirm_purchase(supervisor_client: TestClient, seeded_catalog):
    from pathlib import Path

    sample_xml = Path(__file__).resolve().parent / "fixtures" / "nfe" / "ci_sample_01.xml"
    with sample_xml.open("rb") as handle:
        preview = supervisor_client.post(
            "/purchases/upload-xml",
            files={"file": ("ci_sample_01.xml", handle, "application/xml")},
        )
    assert preview.status_code == 403
