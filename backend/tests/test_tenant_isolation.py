"""Épico 2.5 — isolamento multi-empresa e estoque por loja."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session

from categories.models import Category
from organization.models import Branch, Company, Store
from organization.repository import (
    BranchRepository,
    CompanyRepository,
    StoreRepository,
)
from products.models import Product
from products.service import ProductService
from shared.identity.pdv_credentials import ensure_pdv_id
from shared.identity.security import hash_password
from suppliers.models import Supplier
from tests.conftest import make_client, page_items
from users.models import User
from users.repository import UserRepository
from utils.cpf import build_cpf
from utils.enums import UserProfile


def _create_second_org(session: Session) -> tuple[Company, Branch, Store, User]:
    company = CompanyRepository.create(
        session,
        Company(
            legal_name="Outra Empresa Ltda",
            trade_name="Outra",
            document="11222333000181",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    )
    branch = BranchRepository.create(
        session,
        Branch(
            company_id=company.id,
            name="Filial B",
            code="FILIAL-B",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    )
    store = StoreRepository.create(
        session,
        Store(
            company_id=company.id,
            branch_id=branch.id,
            name="Loja B",
            code="LOJA-B",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    )
    admin_b = User(
        full_name="Admin Empresa B",
        cpf=build_cpf(999),
        email="adminb@test.local",
        username="adminb",
        password_hash=hash_password("adminb123"),
        profile=UserProfile.ADMIN,
        is_active=True,
        company_id=company.id,
        default_branch_id=branch.id,
        default_store_id=store.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    UserRepository.create(session, admin_b)
    ensure_pdv_id(session, admin_b)
    session.add(admin_b)
    session.commit()
    session.refresh(admin_b)
    return company, branch, store, admin_b


def test_auth_me_includes_company_and_store(client: TestClient):
    response = client.get("/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["company_id"] is not None
    assert body["company"]["legal_name"]
    assert body["default_store"]["code"] == "LOJA-CENTRO"
    assert body["default_branch"]["code"] == "MATRIZ"


def test_company_isolation_categories(client: TestClient, test_engine, category: dict):
    with Session(test_engine) as session:
        _company, _branch, _store, _admin = _create_second_org(session)

    client_b = make_client(
        test_engine,
        username="adminb",
        password="adminb123",
        company_document="11222333000181",
    )
    try:
        list_a = client.get("/categories/")
        assert list_a.status_code == 200
        assert any(c["id"] == category["id"] for c in page_items(list_a))

        list_b = client_b.get("/categories/")
        assert list_b.status_code == 200
        assert page_items(list_b) == []

        detail_b = client_b.get(f"/categories/{category['id']}")
        assert detail_b.status_code == 404
    finally:
        client_b.app.dependency_overrides.clear()


def test_sale_requires_valid_store(client: TestClient, stocked_product: dict, test_engine):
    response = client.post(
        "/sales/",
        json={
            "store_id": 999999,
            "items": [{"product_id": stocked_product["id"], "quantity": 1}],
        },
    )
    assert response.status_code == 422

    ok = client.post(
        "/sales/",
        json={"items": [{"product_id": stocked_product["id"], "quantity": 1}]},
    )
    assert ok.status_code == 201
    assert ok.json()["store_id"] is not None
    assert ok.json()["company_id"] is not None


def test_stock_balance_is_per_store(client: TestClient, product: dict, test_engine, db_session):
    me = client.get("/auth/me").json()
    company_id = me["company_id"]
    store_a_id = me["default_store"]["id"]

    branch = BranchRepository.create(
        db_session,
        Branch(
            company_id=company_id,
            name="Filial 2",
            code="FILIAL-2",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    )
    store_b = StoreRepository.create(
        db_session,
        Store(
            company_id=company_id,
            branch_id=branch.id,
            name="Loja 2",
            code="LOJA-2",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    )
    db_session.commit()

    move_a = client.post(
        "/stock/move",
        json={
            "product_id": product["id"],
            "quantity": "10",
            "type": "E",
            "reason": "compra",
            "store_id": store_a_id,
        },
    )
    assert move_a.status_code == 201

    move_b = client.post(
        "/stock/move",
        json={
            "product_id": product["id"],
            "quantity": "3",
            "type": "E",
            "reason": "compra",
            "store_id": store_b.id,
        },
    )
    assert move_b.status_code == 201

    bal_a = client.get(
        f"/stock/product/{product['id']}/balance",
        params={"store_id": store_a_id},
    )
    bal_b = client.get(
        f"/stock/product/{product['id']}/balance",
        params={"store_id": store_b.id},
    )
    assert bal_a.status_code == 200
    assert bal_b.status_code == 200
    assert float(bal_a.json()["current_balance"]) == 10.0
    assert float(bal_b.json()["current_balance"]) == 3.0


def test_jwt_contains_company_id(client: TestClient, admin_token: str):
    from jose import jwt

    from shared.identity.security import JWT_ALGORITHM, JWT_SECRET

    payload = jwt.decode(admin_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert "company_id" in payload
    assert isinstance(payload["company_id"], int)


def test_second_company_can_reuse_sku(
    client: TestClient, test_engine, category: dict, product: dict
):
    with Session(test_engine) as session:
        company, branch, store, _admin = _create_second_org(session)
        cat_b = Category(
            name="Cat B",
            slug="eletronicos",
            is_active=True,
            company_id=company.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(cat_b)
        session.flush()
        supplier_b = Supplier(
            name="Fornecedor B",
            document="11222333000181",
            is_active=True,
            company_id=company.id,
        )
        session.add(supplier_b)
        session.flush()
        prod_b = Product(
            material_code=ProductService(session).allocate_material_code(company.id),
            primary_supplier_id=supplier_b.id,
            name="Mouse B",
            sku=product["sku"],
            sale_price=product["sale_price"],
            cost_price=product["cost_price"],
            category_id=cat_b.id,
            company_id=company.id,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(prod_b)
        session.commit()

    client_b = make_client(
        test_engine,
        username="adminb",
        password="adminb123",
        company_document="11222333000181",
    )
    try:
        products_b = client_b.get("/products/")
        assert products_b.status_code == 200
        items_b = page_items(products_b)
        assert len(items_b) == 1
        assert items_b[0]["sku"] == product["sku"]

        products_a = client.get("/products/")
        items_a = page_items(products_a)
        assert len(items_a) == 1
        assert items_a[0]["id"] != items_b[0]["id"]
    finally:
        client_b.app.dependency_overrides.clear()


def test_company_isolation_customers_and_products_cross_tenant(
    client: TestClient, test_engine, product: dict
):
    created = client.post(
        "/customers/",
        json={"name": "Cliente A", "document": "11144477735", "customer_type": "F"},
    )
    assert created.status_code == 201
    customer_id = created.json()["id"]

    with Session(test_engine) as session:
        _create_second_org(session)

    client_b = make_client(
        test_engine,
        username="adminb",
        password="adminb123",
        company_document="11222333000181",
    )
    try:
        assert client_b.get(f"/customers/{customer_id}").status_code == 404
        assert client_b.get(f"/products/{product['id']}").status_code == 404
        assert page_items(client_b.get("/customers/")) == []
        assert all(p["id"] != product["id"] for p in page_items(client_b.get("/products/")))
    finally:
        client_b.app.dependency_overrides.clear()


def test_company_isolation_purchases(client: TestClient, test_engine, seeded_catalog):
    from pathlib import Path

    sample = Path(__file__).resolve().parent / "fixtures" / "nfe" / "ci_sample_01.xml"
    with sample.open("rb") as handle:
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
        "supplier_document": "12345678000195",
        "supplier_address": preview["supplier"]["address"],
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
    purchase = response.json()

    with Session(test_engine) as session:
        _create_second_org(session)

    client_b = make_client(
        test_engine,
        username="adminb",
        password="adminb123",
        company_document="11222333000181",
    )
    try:
        assert client_b.get(f"/purchases/{purchase['id']}").status_code == 404
        assert all(p["id"] != purchase["id"] for p in page_items(client_b.get("/purchases/")))
    finally:
        client_b.app.dependency_overrides.clear()
