from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import page_items

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "nfe"
SAMPLE_XML = FIXTURES_DIR / "ci_sample_01.xml"


def _confirm_purchase(client: TestClient) -> dict:
    with SAMPLE_XML.open("rb") as handle:
        preview = client.post(
            "/purchases/upload-xml",
            files={"file": ("ci_sample_01.xml", handle, "application/xml")},
        ).json()

    confirm_payload = {
        "access_key": preview["invoice"]["access_key"],
        "invoice_number": preview["invoice"]["invoice_number"],
        "invoice_series": preview["invoice"]["invoice_series"],
        "issue_date": preview["invoice"]["issue_date"],
        "create_supplier": True,
        "supplier_name": preview["supplier"]["name"],
        "supplier_trade_name": preview["supplier"]["trade_name"],
        "supplier_document": preview["supplier"]["document"],
        "supplier_state_registration": preview["supplier"]["state_registration"],
        "items": [
            {
                "supplier_product_code": item["supplier_product_code"],
                "quantity": item["quantity"],
                "unit_cost": item["entry_unit_cost"],
                "discount": item["discount"],
                "ipi_amount": item["ipi_amount"],
                "icms_st_amount": item["icms_st_amount"],
                "total_cost": item["total_cost"],
                "product_id": item["suggested_product_id"],
            }
            for item in preview["items"]
        ],
    }
    response = client.post("/purchases/confirm", json=confirm_payload)
    assert response.status_code == 201
    return response.json()


def test_upload_xml_preview_maps_products_by_barcode(client: TestClient, seeded_catalog):
    with SAMPLE_XML.open("rb") as handle:
        response = client.post(
            "/purchases/upload-xml",
            files={"file": ("ci_sample_01.xml", handle, "application/xml")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["supplier"]["document"] == "20202020000120"
    assert payload["supplier"]["exists_in_database"] is False
    assert len(payload["items"]) == 6
    assert all(item["mapping_status"] == "mapped" for item in payload["items"])


def test_confirm_purchase_creates_supplier_stock_and_updates_cost(
    client: TestClient, seeded_catalog
):
    purchase = _confirm_purchase(client)
    assert purchase["status"] == "Confirmado"
    assert purchase["supplier_name"] == "LimpezaTotal Profissional"
    assert len(purchase["items"]) == 6

    with SAMPLE_XML.open("rb") as handle:
        preview = client.post(
            "/purchases/upload-xml",
            files={"file": ("ci_sample_01.xml", handle, "application/xml")},
        ).json()

    product_id = preview["items"][0]["suggested_product_id"]
    balance = client.get(f"/stock/product/{product_id}/balance")
    assert balance.status_code == 200
    assert Decimal(balance.json()["current_balance"]) > 0

    suppliers = client.get("/suppliers/", params={"document": preview["supplier"]["document"]})
    assert suppliers.status_code == 200
    assert len(page_items(suppliers)) == 1


def test_duplicate_invoice_key_rejected(client: TestClient, seeded_catalog):
    with SAMPLE_XML.open("rb") as handle:
        preview = client.post(
            "/purchases/upload-xml",
            files={"file": ("ci_sample_01.xml", handle, "application/xml")},
        ).json()

    confirm_payload = {
        "access_key": preview["invoice"]["access_key"],
        "invoice_number": preview["invoice"]["invoice_number"],
        "invoice_series": preview["invoice"]["invoice_series"],
        "issue_date": preview["invoice"]["issue_date"],
        "create_supplier": True,
        "supplier_name": preview["supplier"]["name"],
        "supplier_document": preview["supplier"]["document"],
        "items": [
            {
                "supplier_product_code": item["supplier_product_code"],
                "quantity": item["quantity"],
                "unit_cost": item["entry_unit_cost"],
                "discount": item["discount"],
                "ipi_amount": item["ipi_amount"],
                "icms_st_amount": item["icms_st_amount"],
                "total_cost": item["total_cost"],
                "product_id": item["suggested_product_id"],
            }
            for item in preview["items"]
        ],
    }

    assert client.post("/purchases/confirm", json=confirm_payload).status_code == 201
    duplicate = client.post("/purchases/confirm", json=confirm_payload)
    assert duplicate.status_code == 422


def test_cancel_purchase_reverses_stock(client: TestClient, seeded_catalog):
    with SAMPLE_XML.open("rb") as handle:
        preview = client.post(
            "/purchases/upload-xml",
            files={"file": ("ci_sample_01.xml", handle, "application/xml")},
        ).json()

    confirm_payload = {
        "access_key": preview["invoice"]["access_key"],
        "invoice_number": preview["invoice"]["invoice_number"],
        "invoice_series": preview["invoice"]["invoice_series"],
        "issue_date": preview["invoice"]["issue_date"],
        "create_supplier": True,
        "supplier_name": preview["supplier"]["name"],
        "supplier_document": preview["supplier"]["document"],
        "items": [
            {
                "supplier_product_code": item["supplier_product_code"],
                "quantity": item["quantity"],
                "unit_cost": item["entry_unit_cost"],
                "discount": item["discount"],
                "ipi_amount": item["ipi_amount"],
                "icms_st_amount": item["icms_st_amount"],
                "total_cost": item["total_cost"],
                "product_id": item["suggested_product_id"],
            }
            for item in preview["items"]
        ],
    }
    purchase = client.post("/purchases/confirm", json=confirm_payload).json()
    product_id = preview["items"][0]["suggested_product_id"]
    before = Decimal(client.get(f"/stock/product/{product_id}/balance").json()["current_balance"])

    cancel = client.post(f"/purchases/{purchase['id']}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "Cancelado"

    after = Decimal(client.get(f"/stock/product/{product_id}/balance").json()["current_balance"])
    first_qty = Decimal(preview["items"][0]["quantity"])
    assert after == before - first_qty


def test_cancel_purchase_insufficient_stock_returns_409(client: TestClient, seeded_catalog):
    with SAMPLE_XML.open("rb") as handle:
        preview = client.post(
            "/purchases/upload-xml",
            files={"file": ("ci_sample_01.xml", handle, "application/xml")},
        ).json()

    confirm_payload = {
        "access_key": preview["invoice"]["access_key"],
        "invoice_number": preview["invoice"]["invoice_number"],
        "invoice_series": preview["invoice"]["invoice_series"],
        "issue_date": preview["invoice"]["issue_date"],
        "create_supplier": True,
        "supplier_name": preview["supplier"]["name"],
        "supplier_document": preview["supplier"]["document"],
        "items": [
            {
                "supplier_product_code": item["supplier_product_code"],
                "quantity": item["quantity"],
                "unit_cost": item["entry_unit_cost"],
                "discount": item["discount"],
                "ipi_amount": item["ipi_amount"],
                "icms_st_amount": item["icms_st_amount"],
                "total_cost": item["total_cost"],
                "product_id": item["suggested_product_id"],
            }
            for item in preview["items"]
        ],
    }
    purchase = client.post("/purchases/confirm", json=confirm_payload).json()
    product_id = preview["items"][0]["suggested_product_id"]
    balance = Decimal(client.get(f"/stock/product/{product_id}/balance").json()["current_balance"])

    # Consome todo o estoque para impedir o estorno no cancelamento.
    deplete = client.post(
        "/stock/move",
        json={
            "product_id": product_id,
            "quantity": str(balance),
            "type": "S",
            "reason": "ajuste",
        },
    )
    assert deplete.status_code == 201

    cancel = client.post(f"/purchases/{purchase['id']}/cancel")
    assert cancel.status_code == 409
    assert "insufficient stock" in cancel.json()["detail"].lower()


def test_operador_cannot_confirm_purchase(operador_client: TestClient, seeded_catalog):
    with SAMPLE_XML.open("rb") as handle:
        response = operador_client.post(
            "/purchases/upload-xml",
            files={"file": ("ci_sample_01.xml", handle, "application/xml")},
        )
    assert response.status_code == 403


def test_conferente_can_upload_preview(conferente_client: TestClient, seeded_catalog):
    with SAMPLE_XML.open("rb") as handle:
        response = conferente_client.post(
            "/purchases/upload-xml",
            files={"file": ("ci_sample_01.xml", handle, "application/xml")},
        )
    assert response.status_code == 200


def test_supplier_crud(client: TestClient):
    create = client.post(
        "/suppliers/",
        json={
            "name": "Fornecedor Teste Ltda",
            "trade_name": "Fornecedor Teste",
            "document": "11222333000144",
            "state_registration": "1234567890",
            "email": "teste@fornecedor.fake",
            "phone": "11999990000",
            "is_active": True,
        },
    )
    assert create.status_code == 201
    supplier_id = create.json()["id"]

    listing = client.get("/suppliers/", params={"document": "11222333000144"})
    assert listing.status_code == 200
    assert len(page_items(listing)) == 1

    deleted = client.delete(f"/suppliers/{supplier_id}")
    assert deleted.status_code == 204
    assert client.get(f"/suppliers/{supplier_id}").status_code == 404


def test_list_purchases_with_filters(client: TestClient, seeded_catalog):
    purchase = _confirm_purchase(client)

    listing = client.get("/purchases/", params={"status": "Confirmado"})
    assert listing.status_code == 200
    assert any(p["id"] == purchase["id"] for p in page_items(listing))

    by_supplier = client.get("/purchases/", params={"supplier_id": purchase["supplier_id"]})
    assert by_supplier.status_code == 200
    assert len(page_items(by_supplier)) >= 1


def test_list_purchases_filters_by_date_range(client: TestClient, seeded_catalog):
    from datetime import datetime, timedelta

    purchase = _confirm_purchase(client)
    entry_date = datetime.fromisoformat(purchase["entry_date"])

    inside = client.get(
        "/purchases/",
        params={
            "date_from": (entry_date - timedelta(minutes=1)).isoformat(),
            "date_to": (entry_date + timedelta(minutes=1)).isoformat(),
        },
    )
    assert inside.status_code == 200
    assert any(p["id"] == purchase["id"] for p in page_items(inside))

    outside = client.get(
        "/purchases/",
        params={
            "date_from": (entry_date + timedelta(days=1)).isoformat(),
            "date_to": (entry_date + timedelta(days=2)).isoformat(),
        },
    )
    assert outside.status_code == 200
    assert all(p["id"] != purchase["id"] for p in page_items(outside))


def test_get_purchase_detail(client: TestClient, seeded_catalog):
    purchase = _confirm_purchase(client)

    response = client.get(f"/purchases/{purchase['id']}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["supplier_name"] == "LimpezaTotal Profissional"
    assert len(detail["items"]) == 6
    assert detail["items"][0]["product_id"] is not None


def test_get_nonexistent_purchase_returns_404(client: TestClient):
    response = client.get("/purchases/99999")
    assert response.status_code == 404
