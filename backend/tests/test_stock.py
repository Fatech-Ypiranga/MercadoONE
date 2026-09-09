from decimal import Decimal


def test_stock_entry_increases_balance(client, product):
    response = client.post(
        "/stock/move",
        json={
            "product_id": product["id"],
            "quantity": "10",
            "type": "E",
            "reason": "compra",
        },
    )
    assert response.status_code == 201

    balance = client.get(f"/stock/product/{product['id']}/balance")
    assert balance.status_code == 200
    assert Decimal(str(balance.json()["current_balance"])) == Decimal("10")


def test_stock_exit_decreases_balance(client, stocked_product):
    product_id = stocked_product["id"]

    response = client.post(
        "/stock/move",
        json={
            "product_id": product_id,
            "quantity": "5",
            "type": "S",
            "reason": "ajuste",
        },
    )
    assert response.status_code == 201

    balance = client.get(f"/stock/product/{product_id}/balance")
    assert Decimal(str(balance.json()["current_balance"])) == Decimal("15")


def test_stock_exit_without_balance_returns_400(client, product):
    response = client.post(
        "/stock/move",
        json={
            "product_id": product["id"],
            "quantity": "1",
            "type": "S",
            "reason": "ajuste",
        },
    )
    assert response.status_code == 400


def test_stock_extract_lists_movements(client, stocked_product):
    product_id = stocked_product["id"]

    response = client.get(f"/stock/product/{product_id}/extract")
    assert response.status_code == 200
    assert len(response.json()) == 1
