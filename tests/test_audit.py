from fastapi.testclient import TestClient

from tests.conftest import page_items


def test_admin_sees_audit_log_after_product_create(client: TestClient, category: dict):
    product = client.post(
        "/products/",
        json={
            "name": "Auditável",
            "sku": "AUD-001",
            "sale_price": "15.00",
            "cost_price": "8.00",
            "category_id": category["id"],
        },
    ).json()

    response = client.get("/audit-log/", params={"entity_type": "product"})
    assert response.status_code == 200
    logs = page_items(response)
    assert any(log["entity_id"] == product["id"] and log["action"] == "CREATE" for log in logs)


def test_admin_sees_audit_log_after_sale(client: TestClient, stocked_product: dict):
    product_id = stocked_product["id"]
    sale = client.post(
        "/sales/",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
    ).json()

    response = client.get("/audit-log/", params={"entity_type": "sale"})
    assert response.status_code == 200
    logs = page_items(response)
    assert any(log["entity_id"] == sale["id"] for log in logs)


def test_operador_cannot_access_audit_log(operador_client: TestClient):
    response = operador_client.get("/audit-log/")
    assert response.status_code == 403


def test_audit_log_filters_by_user_id(client: TestClient, category: dict, admin_token: str):
    from jose import jwt

    from auth.security import JWT_ALGORITHM, JWT_SECRET

    payload = jwt.decode(admin_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    admin_id = int(payload["sub"])

    client.post(
        "/products/",
        json={
            "name": "Filtro Audit",
            "sku": "FIL-001",
            "sale_price": "12.00",
            "cost_price": "6.00",
            "category_id": category["id"],
        },
    )

    response = client.get("/audit-log/", params={"user_id": admin_id, "entity_type": "product"})
    assert response.status_code == 200
    logs = page_items(response)
    assert len(logs) >= 1
    assert all(log["user_id"] == admin_id for log in logs)


def test_audit_log_pagination(client: TestClient, category: dict):
    for i in range(3):
        client.post(
            "/products/",
            json={
                "name": f"Pag {i}",
                "sku": f"PAG-{i:03d}",
                "sale_price": "10.00",
                "cost_price": "5.00",
                "category_id": category["id"],
            },
        )

    page = client.get("/audit-log/", params={"entity_type": "product", "offset": 0, "limit": 2})
    assert page.status_code == 200
    body = page.json()
    assert len(body["items"]) <= 2
    assert "total" in body
    assert body["offset"] == 0
    assert body["limit"] == 2


def test_audit_log_filters_by_date_range(client: TestClient, category: dict):
    from datetime import datetime, timedelta, timezone

    product = client.post(
        "/products/",
        json={
            "name": "Audit Date Filter",
            "sku": "ADF-001",
            "sale_price": "11.00",
            "cost_price": "5.50",
            "category_id": category["id"],
        },
    ).json()

    logs = page_items(client.get("/audit-log/", params={"entity_type": "product"}))
    created = next(log for log in logs if log["entity_id"] == product["id"])
    created_at = datetime.fromisoformat(created["created_at"])

    inside = client.get(
        "/audit-log/",
        params={
            "entity_type": "product",
            "date_from": (created_at - timedelta(minutes=1)).isoformat(),
            "date_to": (created_at + timedelta(minutes=1)).isoformat(),
        },
    )
    assert inside.status_code == 200
    assert any(log["entity_id"] == product["id"] for log in page_items(inside))

    outside = client.get(
        "/audit-log/",
        params={
            "entity_type": "product",
            "date_from": (created_at + timedelta(days=1)).isoformat(),
            "date_to": (created_at + timedelta(days=2)).isoformat(),
        },
    )
    assert outside.status_code == 200
    assert all(log["entity_id"] != product["id"] for log in page_items(outside))

    past = client.get(
        "/audit-log/",
        params={
            "entity_type": "product",
            "date_from": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "date_to": (created_at - timedelta(minutes=1)).isoformat(),
        },
    )
    assert past.status_code == 200
    assert all(log["entity_id"] != product["id"] for log in page_items(past))
