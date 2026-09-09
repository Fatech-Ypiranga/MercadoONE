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
