from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from models.product import Product


def test_create_product_with_fiscal(client: TestClient, category: dict):
    response = client.post(
        "/products/",
        json={
            "name": "Arroz 5kg",
            "sku": "ARR-001",
            "barcode": "7891234567890",
            "sale_price": "25.90",
            "cost_price": "18.00",
            "category_id": category["id"],
            "fiscal": {
                "ncm": "10063021",
                "cfop_default": "5102",
                "origem_produto": 0,
            },
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Arroz 5kg"
    assert data["fiscal"]["ncm"] == "10063021"
    assert data["category"]["id"] == category["id"]


def test_update_product(client: TestClient, product: dict):
    response = client.put(
        f"/products/{product['id']}",
        json={"name": "Mouse Gamer Pro", "sale_price": "75.00"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Mouse Gamer Pro"
    assert Decimal(str(response.json()["sale_price"])) == Decimal("75.00")


def test_hard_delete_product(client: TestClient, product: dict, db_session: Session):
    response = client.delete(f"/products/{product['id']}")
    assert response.status_code == 204

    detail = client.get(f"/products/{product['id']}")
    assert detail.status_code == 404

    db_product = db_session.exec(select(Product).where(Product.id == product["id"])).first()
    assert db_product is None


def test_delete_product_with_stock_returns_409(client: TestClient, stocked_product: dict):
    response = client.delete(f"/products/{stocked_product['id']}")
    assert response.status_code == 409


def test_create_product_with_zero_price_returns_422(client: TestClient, category: dict):
    response = client.post(
        "/products/",
        json={
            "name": "Inválido",
            "sku": "INV-001",
            "sale_price": "0",
            "cost_price": "5.00",
            "category_id": category["id"],
        },
    )
    assert response.status_code == 422


def test_create_product_with_nonexistent_category_returns_404(client: TestClient):
    response = client.post(
        "/products/",
        json={
            "name": "Sem Categoria",
            "sku": "SEM-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": 99999,
        },
    )
    assert response.status_code == 404


def test_product_weight_defaults_are_decimal(client: TestClient, category: dict):
    response = client.post(
        "/products/",
        json={
            "name": "Peso Teste",
            "sku": "PES-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": category["id"],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert Decimal(str(data["weight_net"])) == Decimal("0")
    assert Decimal(str(data["weight_gross"])) == Decimal("0")
