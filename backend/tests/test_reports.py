from decimal import Decimal


def test_top_products_report(client, stocked_product):
    product_id = stocked_product["id"]

    client.post("/sales/", json={"items": [{"product_id": product_id, "quantity": 7}]})
    client.post("/sales/", json={"items": [{"product_id": product_id, "quantity": 3}]})

    response = client.get("/reports/top-products", params={"limit": 5})
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == product_id
    assert data[0]["total_sold"] == 10


def test_average_ticket_report(client, stocked_product):
    product_id = stocked_product["id"]

    client.post("/sales/", json={"items": [{"product_id": product_id, "quantity": 2}]})
    client.post("/sales/", json={"items": [{"product_id": product_id, "quantity": 4}]})

    response = client.get("/reports/average-ticket")
    assert response.status_code == 200
    assert Decimal(str(response.json()["average_ticket"])) == Decimal("150.00")


def test_critical_stock_report(client, product):
    response = client.get("/reports/critical-stock", params={"min_threshold": 5})
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == product["id"]
    assert data[0]["current_stock"] == 0
    assert Decimal(str(data[0]["min_stock"])) == Decimal("5")

    client.post(
        "/stock/move",
        json={
            "product_id": product["id"],
            "quantity": "10",
            "type": "E",
            "reason": "compra",
        },
    )

    response = client.get("/reports/critical-stock", params={"min_threshold": 5})
    assert response.json() == []


def test_critical_stock_uses_product_min_stock(client, product):
    update = client.put(
        f"/products/{product['id']}",
        json={"min_stock": "20"},
    )
    assert update.status_code == 200
    assert Decimal(str(update.json()["min_stock"])) == Decimal("20")

    client.post(
        "/stock/move",
        json={
            "product_id": product["id"],
            "quantity": "10",
            "type": "E",
            "reason": "compra",
        },
    )

    # Below product min (20) even though above global fallback (5)
    response = client.get("/reports/critical-stock", params={"min_threshold": 5})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == product["id"]
    assert Decimal(str(data[0]["current_stock"])) == Decimal("10")
    assert Decimal(str(data[0]["min_stock"])) == Decimal("20")

    client.post(
        "/stock/move",
        json={
            "product_id": product["id"],
            "quantity": "15",
            "type": "E",
            "reason": "compra",
        },
    )

    # Now above product min
    response = client.get("/reports/critical-stock", params={"min_threshold": 5})
    assert response.json() == []


def test_sales_by_operator_groups_and_skips_cancelled(client, stocked_product):
    product_id = stocked_product["id"]  # sale price 50.00
    client.post("/sales/", json={"items": [{"product_id": product_id, "quantity": 2}]})  # 100
    client.post("/sales/", json={"items": [{"product_id": product_id, "quantity": 1}]})  # 50
    cancelled = client.post(
        "/sales/", json={"items": [{"product_id": product_id, "quantity": 5}]}
    ).json()
    client.post(f"/sales/{cancelled['id']}/cancel")

    response = client.get("/reports/sales-by-operator")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["sales_count"] == 2
    assert Decimal(rows[0]["total_amount"]) == Decimal("150.00")
    assert Decimal(rows[0]["average_ticket"]) == Decimal("75.00")


def test_sales_by_operator_respects_date_filter(client, stocked_product):
    client.post("/sales/", json={"items": [{"product_id": stocked_product["id"], "quantity": 1}]})
    assert client.get("/reports/sales-by-operator", params={"date_to": "2000-01-01"}).json() == []
    assert (
        len(client.get("/reports/sales-by-operator", params={"date_from": "2000-01-01"}).json())
        == 1
    )


def test_sales_by_customer_only_lists_identified_customers(client, stocked_product):
    from utils.cpf import build_cpf

    product_id = stocked_product["id"]
    customer = client.post(
        "/customers/",
        json={
            "name": "Maria Cliente",
            "customer_type": "F",
            "document": build_cpf(777),
            "is_active": True,
            "addresses": [],
        },
    )
    assert customer.status_code == 201, customer.text
    customer_id = customer.json()["id"]

    client.post(
        "/sales/",
        json={"customer_id": customer_id, "items": [{"product_id": product_id, "quantity": 2}]},
    )
    client.post("/sales/", json={"items": [{"product_id": product_id, "quantity": 1}]})  # anonymous

    rows = client.get("/reports/sales-by-customer").json()
    assert len(rows) == 1
    assert rows[0]["id"] == customer_id
    assert rows[0]["name"] == "Maria Cliente"
    assert Decimal(rows[0]["total_amount"]) == Decimal("100.00")


def test_sales_reports_require_authentication(client):
    anonymous = client.__class__(client.app)
    assert anonymous.get("/reports/sales-by-operator").status_code in (401, 403)
    assert anonymous.get("/reports/sales-by-customer").status_code in (401, 403)
