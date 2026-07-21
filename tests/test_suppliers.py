import re
from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from models.company import Store
from models.purchase import PurchaseOrder
from models.supplier import Supplier
from models.user import User
from tests.conftest import page_items
from utils.enums import PurchaseStatus

VALID_CNPJ_FORMATTED = "11.222.333/0001-81"
VALID_CNPJ_NORMALIZED = "11222333000181"


def address_payload(**overrides) -> dict:
    payload = {
        "description": "Principal",
        "zip_code": "01310100",
        "street": "Avenida Paulista",
        "number": "1000",
        "complement": "Sala 1",
        "neighborhood": "Bela Vista",
        "city": "São Paulo",
        "state": "SP",
        "ibge_code": "3550308",
    }
    payload.update(overrides)
    return payload


def supplier_payload(**overrides) -> dict:
    payload = {
        "name": "Fornecedor ACME LTDA",
        "trade_name": "ACME",
        "document": VALID_CNPJ_FORMATTED,
        "state_registration": "1234567890",
        "email": "contato@acme.test",
        "phone": "11999990000",
        "is_active": True,
        "address": address_payload(),
    }
    payload.update(overrides)
    return payload


def test_create_supplier_with_invalid_cnpj_returns_422(client: TestClient):
    response = client.post(
        "/suppliers/",
        json=supplier_payload(document="11222333000182"),
    )

    assert response.status_code == 422
    assert "cnpj" in response.json()["detail"].lower()


def test_create_supplier_persists_valid_cnpj_and_state_registration(client: TestClient):
    response = client.post("/suppliers/", json=supplier_payload())

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Fornecedor ACME LTDA"
    assert data["trade_name"] == "ACME"
    assert data["document"] == VALID_CNPJ_NORMALIZED
    assert data["state_registration"] == "1234567890"
    assert data["email"] == "contato@acme.test"
    assert data["phone"] == "11999990000"
    assert data["is_active"] is True
    assert re.fullmatch(r"\d{8}", data["code"])
    assert data["code"].startswith("35")
    assert data["address"]["ibge_code"] == "3550308"


def test_create_supplier_requires_complete_address(client: TestClient):
    missing = client.post("/suppliers/", json=supplier_payload(address=None))
    incomplete = client.post(
        "/suppliers/",
        json=supplier_payload(
            document="12.345.678/0001-95",
            address=address_payload(neighborhood=""),
        ),
    )

    assert missing.status_code == 422
    assert incomplete.status_code == 422


def test_create_supplier_rejects_uf_ibge_mismatch(client: TestClient):
    response = client.post(
        "/suppliers/",
        json=supplier_payload(address=address_payload(state="RJ")),
    )

    assert response.status_code == 422


def test_same_municipality_reuses_mmm_and_increments_company_sequence(client: TestClient):
    first = client.post("/suppliers/", json=supplier_payload()).json()
    second_response = client.post(
        "/suppliers/",
        json=supplier_payload(
            name="Fornecedor B",
            document="12.345.678/0001-95",
        ),
    )

    assert second_response.status_code == 201
    second = second_response.json()
    assert first["code"][2:5] == second["code"][2:5]
    assert int(second["code"][5:]) == int(first["code"][5:]) + 1


def test_different_municipality_gets_different_mmm(client: TestClient):
    first = client.post("/suppliers/", json=supplier_payload()).json()
    second_response = client.post(
        "/suppliers/",
        json=supplier_payload(
            name="Fornecedor Campinas",
            document="12.345.678/0001-95",
            address=address_payload(
                zip_code="13010001",
                city="Campinas",
                ibge_code="3509502",
            ),
        ),
    )

    assert second_response.status_code == 201
    second = second_response.json()
    assert first["code"][2:5] != second["code"][2:5]


def test_supplier_codes_are_isolated_per_company(
    client: TestClient, second_company_client: TestClient
):
    first = client.post("/suppliers/", json=supplier_payload())
    second = second_company_client.post("/suppliers/", json=supplier_payload())

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["code"] == second.json()["code"]
    assert second_company_client.get(f"/suppliers/{first.json()['id']}").status_code == 404


def test_update_address_preserves_supplier_code(client: TestClient):
    created = client.post("/suppliers/", json=supplier_payload()).json()
    updated_address = address_payload(number="2000", complement=None)

    response = client.put(
        f"/suppliers/{created['id']}",
        json={"address": updated_address, "code": "99999999"},
    )

    assert response.status_code == 200
    assert response.json()["code"] == created["code"]
    assert response.json()["address"]["number"] == "2000"
    assert response.json()["address"]["ibge_code"] == "3550308"


def test_create_ignores_client_supplied_supplier_code(client: TestClient):
    response = client.post(
        "/suppliers/",
        json={**supplier_payload(), "code": "99999999"},
    )

    assert response.status_code == 201
    assert response.json()["code"] != "99999999"


def test_legacy_supplier_is_regularized_on_next_update(client: TestClient, db_session: Session):
    user = db_session.exec(select(User).order_by(User.id)).first()
    assert user is not None
    legacy = Supplier(
        company_id=user.company_id,
        name="Fornecedor Legado",
        document="12345678000195",
    )
    db_session.add(legacy)
    db_session.commit()
    db_session.refresh(legacy)

    missing_address = client.put(f"/suppliers/{legacy.id}", json={"trade_name": "Legado"})
    assert missing_address.status_code == 422

    response = client.put(
        f"/suppliers/{legacy.id}",
        json={"trade_name": "Legado", "address": address_payload()},
    )

    assert response.status_code == 200
    assert re.fullmatch(r"\d{8}", response.json()["code"])
    assert response.json()["address"]["ibge_code"] == "3550308"


def test_get_supplier_by_document_normalizes_punctuation(client: TestClient):
    create = client.post("/suppliers/", json=supplier_payload())
    assert create.status_code == 201
    created = create.json()

    response = client.get(f"/suppliers/by-document/{VALID_CNPJ_FORMATTED}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created["id"]
    assert data["document"] == VALID_CNPJ_NORMALIZED


def test_duplicate_supplier_document_returns_409(client: TestClient):
    first = client.post("/suppliers/", json=supplier_payload())
    assert first.status_code == 201

    response = client.post(
        "/suppliers/",
        json=supplier_payload(name="Fornecedor Duplicado", document=VALID_CNPJ_NORMALIZED),
    )

    assert response.status_code == 409
    assert (
        "document" in response.json()["detail"].lower()
        or "cnpj" in response.json()["detail"].lower()
    )


def test_update_supplier_to_duplicate_document_returns_409(client: TestClient):
    create_a = client.post("/suppliers/", json=supplier_payload())
    assert create_a.status_code == 201
    supplier_a = create_a.json()

    create_b = client.post(
        "/suppliers/",
        json=supplier_payload(
            name="Fornecedor B",
            trade_name="Fornecedor B",
            document="12.345.678/0001-95",
            email="b@acme.test",
        ),
    )
    assert create_b.status_code == 201
    supplier_b = create_b.json()

    response = client.put(
        f"/suppliers/{supplier_b['id']}",
        json={"document": supplier_a["document"]},
    )

    assert response.status_code == 409
    assert (
        "document" in response.json()["detail"].lower()
        or "cnpj" in response.json()["detail"].lower()
    )


def test_delete_supplier_with_purchase_returns_409(client: TestClient, db_session: Session):
    create = client.post("/suppliers/", json=supplier_payload())
    assert create.status_code == 201
    created = create.json()
    supplier = db_session.exec(select(Supplier).where(Supplier.id == created["id"])).first()
    assert supplier is not None

    user = db_session.exec(
        select(User).where(User.company_id == supplier.company_id).order_by(User.id)
    ).first()
    store = db_session.exec(
        select(Store).where(Store.company_id == supplier.company_id).order_by(Store.id)
    ).first()
    assert user is not None
    assert store is not None

    db_session.add(
        PurchaseOrder(
            supplier_id=supplier.id,
            user_id=user.id,
            company_id=supplier.company_id,
            store_id=store.id,
            invoice_number="NF-TEST-001",
            invoice_series="1",
            invoice_key="12345678901234567890123456789012345678901234",
            issue_date=datetime.now(timezone.utc),
            total_amount=Decimal("10.00"),
            status=PurchaseStatus.CONFIRMADO,
            created_by=user.id,
            updated_by=user.id,
        )
    )
    db_session.commit()

    response = client.delete(f"/suppliers/{supplier.id}")

    assert response.status_code == 409
    assert "compras vinculadas" in response.json()["detail"].lower()


def test_delete_supplier_with_primary_product_returns_409(client: TestClient, category: dict):
    supplier = client.post("/suppliers/", json=supplier_payload()).json()
    product = client.post(
        "/products/",
        json={
            "name": "Produto do fornecedor",
            "sku": "SUP-PRIM-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
        },
    )
    assert product.status_code == 201

    response = client.delete(f"/suppliers/{supplier['id']}")

    assert response.status_code == 409
    detail = response.json()["detail"].lower()
    assert "produto" in detail or "primary" in detail or "fornecedor principal" in detail


def test_list_suppliers_filters_by_normalized_document(client: TestClient):
    create = client.post("/suppliers/", json=supplier_payload())
    assert create.status_code == 201

    response = client.get("/suppliers/", params={"document": VALID_CNPJ_FORMATTED})

    assert response.status_code == 200
    items = page_items(response)
    assert len(items) == 1
    assert items[0]["document"] == VALID_CNPJ_NORMALIZED
