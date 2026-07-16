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


def supplier_payload(**overrides) -> dict:
    payload = {
        "name": "Fornecedor ACME LTDA",
        "trade_name": "ACME",
        "document": VALID_CNPJ_FORMATTED,
        "state_registration": "1234567890",
        "email": "contato@acme.test",
        "phone": "11999990000",
        "is_active": True,
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
    assert "document" in response.json()["detail"].lower() or "cnpj" in response.json()[
        "detail"
    ].lower()


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
    assert "document" in response.json()["detail"].lower() or "cnpj" in response.json()[
        "detail"
    ].lower()


def test_delete_supplier_with_purchase_returns_409(
    client: TestClient, db_session: Session
):
    create = client.post("/suppliers/", json=supplier_payload())
    assert create.status_code == 201
    created = create.json()
    supplier = db_session.exec(
        select(Supplier).where(Supplier.id == created["id"])
    ).first()
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


def test_list_suppliers_filters_by_normalized_document(client: TestClient):
    create = client.post("/suppliers/", json=supplier_payload())
    assert create.status_code == 201

    response = client.get("/suppliers/", params={"document": VALID_CNPJ_FORMATTED})

    assert response.status_code == 200
    items = page_items(response)
    assert len(items) == 1
    assert items[0]["document"] == VALID_CNPJ_NORMALIZED
