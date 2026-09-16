import re
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session

from products.models import Product


def _supplier_payload(document: str = "11.222.333/0001-81") -> dict:
    return {
        "name": "Fornecedor principal",
        "document": document,
        "is_active": True,
        "address": {
            "description": "Principal",
            "zip_code": "01310100",
            "street": "Avenida Paulista",
            "number": "1000",
            "neighborhood": "Bela Vista",
            "city": "São Paulo",
            "state": "SP",
            "ibge_code": "3550308",
        },
    }


def _product_payload(category_id: int, supplier_id: int | None = None, **overrides) -> dict:
    payload = {
        "name": "Produto Épico 4",
        "sku": "EP4-001",
        "sale_price": "10.00",
        "cost_price": "5.00",
        "category_id": category_id,
    }
    if supplier_id is not None:
        payload["primary_supplier_id"] = supplier_id
    payload.update(overrides)
    return payload


def test_ordinary_product_create_requires_primary_supplier(client: TestClient, category: dict):
    response = client.post("/products/", json=_product_payload(category["id"]))

    assert response.status_code == 422


def test_created_products_receive_increasing_seven_digit_material_codes(
    client: TestClient, category: dict
):
    supplier = client.post("/suppliers/", json=_supplier_payload()).json()

    first = client.post(
        "/products/",
        json=_product_payload(category["id"], supplier["id"]),
    )
    second = client.post(
        "/products/",
        json=_product_payload(
            category["id"],
            supplier["id"],
            name="Segundo produto",
            sku="EP4-002",
        ),
    )

    assert first.status_code == 201
    assert second.status_code == 201
    first_code = first.json()["material_code"]
    second_code = second.json()["material_code"]
    assert re.fullmatch(r"\d{7}", first_code)
    assert int(second_code) == int(first_code) + 1


def test_product_rejects_primary_supplier_from_another_company(
    client: TestClient,
    second_company_client: TestClient,
    category: dict,
):
    foreign_supplier = second_company_client.post(
        "/suppliers/",
        json=_supplier_payload(),
    ).json()

    response = client.post(
        "/products/",
        json=_product_payload(category["id"], foreign_supplier["id"]),
    )

    assert response.status_code == 404


def test_client_material_code_cannot_override_generated_value(client: TestClient, category: dict):
    supplier = client.post("/suppliers/", json=_supplier_payload()).json()

    response = client.post(
        "/products/",
        json=_product_payload(
            category["id"],
            supplier["id"],
            material_code="7654321",
        ),
    )

    assert response.status_code == 201
    assert response.json()["material_code"] != "7654321"


def test_update_changes_supplier_but_preserves_material_code(client: TestClient, category: dict):
    first_supplier = client.post("/suppliers/", json=_supplier_payload()).json()
    second_supplier = client.post(
        "/suppliers/",
        json=_supplier_payload("12.345.678/0001-95") | {"name": "Segundo fornecedor"},
    ).json()
    created = client.post(
        "/products/",
        json=_product_payload(category["id"], first_supplier["id"]),
    ).json()

    response = client.put(
        f"/products/{created['id']}",
        json={
            "primary_supplier_id": second_supplier["id"],
            "material_code": "9999999",
        },
    )

    assert response.status_code == 200
    assert response.json()["primary_supplier_id"] == second_supplier["id"]
    assert response.json()["material_code"] == created["material_code"]


def test_legacy_product_edit_requires_supplier_regularization(
    client: TestClient,
    category: dict,
    db_session: Session,
):
    supplier = client.post("/suppliers/", json=_supplier_payload()).json()
    legacy = Product(
        company_id=1,
        material_code="9000000",
        primary_supplier_id=None,
        name="Produto legado",
        sku="LEGACY-001",
        cost_price=5,
        sale_price=10,
        category_id=category["id"],
    )
    db_session.add(legacy)
    db_session.commit()
    db_session.refresh(legacy)

    missing = client.put(f"/products/{legacy.id}", json={"name": "Editado"})
    regularized = client.put(
        f"/products/{legacy.id}",
        json={"name": "Editado", "primary_supplier_id": supplier["id"]},
    )

    assert missing.status_code == 422
    assert regularized.status_code == 200
    assert regularized.json()["primary_supplier_id"] == supplier["id"]
    assert regularized.json()["material_code"] == "9000000"


def test_product_list_searches_and_filters_material_code_and_supplier(
    client: TestClient, category: dict
):
    first_supplier = client.post("/suppliers/", json=_supplier_payload()).json()
    second_supplier = client.post(
        "/suppliers/",
        json=_supplier_payload("12.345.678/0001-95") | {"name": "Segundo fornecedor"},
    ).json()
    first = client.post(
        "/products/",
        json=_product_payload(category["id"], first_supplier["id"]),
    ).json()
    client.post(
        "/products/",
        json=_product_payload(
            category["id"],
            second_supplier["id"],
            name="Outro produto",
            sku="EP4-OTHER",
        ),
    )

    by_q = client.get("/products/", params={"q": first["material_code"]}).json()["items"]
    by_code = client.get(
        "/products/",
        params={"material_code": first["material_code"]},
    ).json()["items"]
    by_supplier = client.get(
        "/products/",
        params={"primary_supplier_id": first_supplier["id"]},
    ).json()["items"]

    assert [item["id"] for item in by_q] == [first["id"]]
    assert [item["id"] for item in by_code] == [first["id"]]
    assert [item["id"] for item in by_supplier] == [first["id"]]


def test_brand_domain_is_absent_from_routes_permissions_navigation_and_openapi(
    client: TestClient,
):
    assert client.get("/brands/").status_code == 404
    openapi_text = str(client.app.openapi()).lower()
    assert "brand" not in openapi_text

    root = Path(__file__).resolve().parents[1]
    repo_root = root.parent
    assert '"brands"' not in (
        root / "shared" / "identity" / "permissions.py"
    ).read_text(encoding="utf-8")
    assert "brands:" not in (repo_root / "frontend" / "lib" / "permissions.ts").read_text(
        encoding="utf-8"
    )
    assert "/brands" not in (repo_root / "frontend" / "lib" / "nav.ts").read_text(
        encoding="utf-8"
    )


def test_purchase_inline_product_receives_material_code_and_primary_supplier(
    client: TestClient,
    category: dict,
    supplier: dict,
):
    response = client.post(
        "/purchases/confirm",
        json={
            "access_key": "EPIC4-INLINE-0001",
            "invoice_number": "4001",
            "invoice_series": "1",
            "issue_date": "2026-07-16T12:00:00Z",
            "supplier_id": supplier["id"],
            "items": [
                {
                    "supplier_product_code": "CPROD-EP4",
                    "quantity": "2",
                    "unit_cost": "5.00",
                    "total_cost": "10.00",
                    "create_product": {
                        "name": "Produto criado na compra",
                        "sku": "PUR-EP4-001",
                        "category_id": category["id"],
                        "cost_price": "5.00",
                    },
                }
            ],
        },
    )

    assert response.status_code == 201
    product_id = response.json()["items"][0]["product_id"]
    product = client.get(f"/products/{product_id}").json()
    assert re.fullmatch(r"\d{7}", product["material_code"])
    assert product["primary_supplier_id"] == supplier["id"]


def test_purchase_inline_product_rejects_duplicate_barcode(
    client: TestClient,
    category: dict,
    supplier: dict,
):
    existing = client.post(
        "/products/",
        json=_product_payload(
            category["id"],
            supplier["id"],
            sku="EXISTING-BC",
            barcode="7898888777766",
        ),
    )
    assert existing.status_code == 201

    response = client.post(
        "/purchases/confirm",
        json={
            "access_key": "EPIC4-DUP-BARCODE-0001",
            "invoice_number": "4002",
            "invoice_series": "1",
            "issue_date": "2026-07-16T12:00:00Z",
            "supplier_id": supplier["id"],
            "items": [
                {
                    "supplier_product_code": "CPROD-DUP-BC",
                    "quantity": "1",
                    "unit_cost": "5.00",
                    "total_cost": "5.00",
                    "create_product": {
                        "name": "Produto barcode duplicado",
                        "sku": "PUR-DUP-BC",
                        "barcode": "7898888777766",
                        "category_id": category["id"],
                        "cost_price": "5.00",
                    },
                }
            ],
        },
    )

    assert response.status_code == 409
    detail = response.json()["detail"].lower()
    assert "barcode" in detail or "código de barras" in detail


def test_purchase_inline_product_rejects_non_leaf_category(
    client: TestClient,
    supplier: dict,
):
    root = client.post(
        "/categories/",
        json={"name": "Raiz Compra", "slug": "raiz-compra", "is_active": True},
    ).json()
    client.post(
        "/categories/",
        json={
            "name": "Filho Compra",
            "slug": "filho-compra",
            "is_active": True,
            "parent_id": root["id"],
        },
    )

    response = client.post(
        "/purchases/confirm",
        json={
            "access_key": "EPIC4-NONLEAF-0001",
            "invoice_number": "4003",
            "invoice_series": "1",
            "issue_date": "2026-07-16T12:00:00Z",
            "supplier_id": supplier["id"],
            "items": [
                {
                    "supplier_product_code": "CPROD-NONLEAF",
                    "quantity": "1",
                    "unit_cost": "5.00",
                    "total_cost": "5.00",
                    "create_product": {
                        "name": "Produto categoria raiz",
                        "sku": "PUR-NONLEAF",
                        "category_id": root["id"],
                        "cost_price": "5.00",
                    },
                }
            ],
        },
    )

    assert response.status_code == 422
