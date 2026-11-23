from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME, make_client, page_items


def test_process_sale_deducts_stock_and_returns_items(client, stocked_product):
    product_id = stocked_product["id"]

    response = client.post(
        "/sales/",
        json={
            "payment_method": "pix",
            "items": [{"product_id": product_id, "quantity": 3}],
        },
    )
    assert response.status_code == 201

    sale = response.json()
    assert sale["status"] == "Concluida"
    assert sale["total_amount"] == "150.00"
    assert len(sale["items"]) == 1
    assert sale["items"][0]["product_id"] == product_id
    assert sale["items"][0]["quantity"] == 3

    balance = client.get(f"/stock/product/{product_id}/balance")
    assert Decimal(str(balance.json()["current_balance"])) == Decimal("17")


def test_cancel_sale_restores_stock(client, stocked_product):
    product_id = stocked_product["id"]

    sale_response = client.post(
        "/sales/",
        json={"items": [{"product_id": product_id, "quantity": 4}]},
    )
    sale_id = sale_response.json()["id"]

    cancel_response = client.post(f"/sales/{sale_id}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "Cancelada"

    balance = client.get(f"/stock/product/{product_id}/balance")
    assert Decimal(str(balance.json()["current_balance"])) == Decimal("20")


def test_sale_without_stock_returns_409(client, product):
    response = client.post(
        "/sales/",
        json={"items": [{"product_id": product["id"], "quantity": 1}]},
    )
    assert response.status_code == 409


def test_list_sales_filter_by_status(client, stocked_product):
    product_id = stocked_product["id"]

    client.post("/sales/", json={"items": [{"product_id": product_id, "quantity": 1}]})
    sale = client.post(
        "/sales/", json={"items": [{"product_id": product_id, "quantity": 1}]}
    ).json()
    client.post(f"/sales/{sale['id']}/cancel")

    concluded = client.get("/sales/", params={"status": "Concluida"})
    cancelled = client.get("/sales/", params={"status": "Cancelada"})

    assert concluded.status_code == 200
    assert cancelled.status_code == 200
    assert len(page_items(concluded)) == 1
    assert len(page_items(cancelled)) == 1


def test_concurrent_sales_of_last_unit_one_succeeds_one_fails(test_engine, client, product):
    product_id = product["id"]
    entry = client.post(
        "/stock/move",
        json={
            "product_id": product_id,
            "quantity": "1",
            "type": "E",
            "reason": "compra",
        },
    )
    assert entry.status_code == 201

    def attempt_sale():
        sale_client = make_client(test_engine, username=ADMIN_USERNAME, password=ADMIN_PASSWORD)
        try:
            return sale_client.post(
                "/sales/",
                json={"items": [{"product_id": product_id, "quantity": 1}]},
            )
        finally:
            sale_client.app.dependency_overrides.clear()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: attempt_sale(), range(2)))

    status_codes = sorted(response.status_code for response in results)
    assert status_codes == [201, 409]

    balance = client.get(f"/stock/product/{product_id}/balance")
    assert Decimal(str(balance.json()["current_balance"])) == Decimal("0")


def test_repeated_client_sale_id_returns_original_sale_without_new_movement(
    client, stocked_product
):
    product_id = stocked_product["id"]
    payload = {
        "client_sale_id": "pdv-1-0001",
        "items": [{"product_id": product_id, "quantity": 2}],
    }

    first = client.post("/sales/", json=payload)
    second = client.post("/sales/", json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["client_sale_id"] == "pdv-1-0001"

    balance = client.get(f"/stock/product/{product_id}/balance")
    assert Decimal(str(balance.json()["current_balance"])) == Decimal("18")


def test_distinct_client_sale_ids_create_distinct_sales(client, stocked_product):
    product_id = stocked_product["id"]
    ids = set()
    for key in ("a-1", "a-2"):
        r = client.post(
            "/sales/",
            json={"client_sale_id": key, "items": [{"product_id": product_id, "quantity": 1}]},
        )
        assert r.status_code == 201
        ids.add(r.json()["id"])
    assert len(ids) == 2


def test_sales_without_client_sale_id_are_never_deduplicated(client, stocked_product):
    body = {"items": [{"product_id": stocked_product["id"], "quantity": 1}]}
    first = client.post("/sales/", json=body).json()["id"]
    second = client.post("/sales/", json=body).json()["id"]
    assert first != second


def test_sale_with_split_payments_stores_each_payment(client, stocked_product):
    body = {
        "items": [{"product_id": stocked_product["id"], "quantity": 2}],  # total 100.00
        "payments": [
            {"method": "Dinheiro", "amount": "30.00"},
            {"method": "pix", "amount": "70.00"},
        ],
    }
    response = client.post("/sales/", json=body)
    assert response.status_code == 201
    sale = response.json()
    assert sale["payment_method"] == "multiplo"
    assert [(p["method"], p["amount"]) for p in sale["payments"]] == [
        ("dinheiro", "30.00"),
        ("pix", "70.00"),
    ]
    fetched = client.get(f"/sales/{sale['id']}").json()
    assert len(fetched["payments"]) == 2


def test_split_payments_must_match_total(client, stocked_product):
    for amounts in (["30.00", "60.00"], ["60.00", "50.00"]):
        response = client.post(
            "/sales/",
            json={
                "items": [{"product_id": stocked_product["id"], "quantity": 2}],
                "payments": [{"method": "pix", "amount": a} for a in amounts],
            },
        )
        assert response.status_code in (400, 422)
    balance = client.get(f"/stock/product/{stocked_product['id']}/balance")
    assert Decimal(str(balance.json()["current_balance"])) == Decimal("20")


def test_payment_method_and_payments_together_are_rejected(client, stocked_product):
    response = client.post(
        "/sales/",
        json={
            "items": [{"product_id": stocked_product["id"], "quantity": 1}],
            "payment_method": "pix",
            "payments": [{"method": "pix", "amount": "50.00"}],
        },
    )
    assert response.status_code == 422


def test_legacy_payment_method_creates_single_payment_for_full_total(client, stocked_product):
    sale = client.post(
        "/sales/",
        json={
            "items": [{"product_id": stocked_product["id"], "quantity": 1}],
            "payment_method": "pix",
        },
    ).json()
    assert sale["payment_method"] == "pix"
    assert [(p["method"], p["amount"]) for p in sale["payments"]] == [("pix", "50.00")]
