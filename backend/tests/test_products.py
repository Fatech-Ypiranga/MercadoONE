from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from products.models import Product


def test_create_product_with_fiscal(client: TestClient, category: dict, supplier: dict):
    response = client.post(
        "/products/",
        json={
            "name": "Arroz 5kg",
            "sku": "ARR-001",
            "barcode": "7891234567890",
            "sale_price": "25.90",
            "cost_price": "18.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
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


def test_create_product_with_zero_price_returns_422(
    client: TestClient, category: dict, supplier: dict
):
    response = client.post(
        "/products/",
        json={
            "name": "Inválido",
            "sku": "INV-001",
            "sale_price": "0",
            "cost_price": "5.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
        },
    )
    assert response.status_code == 422


def test_create_product_with_nonexistent_category_returns_404(client: TestClient, supplier: dict):
    response = client.post(
        "/products/",
        json={
            "name": "Sem Categoria",
            "sku": "SEM-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": 99999,
            "primary_supplier_id": supplier["id"],
        },
    )
    assert response.status_code == 404


def test_product_weight_defaults_are_decimal(client: TestClient, category: dict, supplier: dict):
    response = client.post(
        "/products/",
        json={
            "name": "Peso Teste",
            "sku": "PES-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert Decimal(str(data["weight_net"])) == Decimal("0")
    assert Decimal(str(data["weight_gross"])) == Decimal("0")


# --- Épico 3: Produto (API) ---


def test_get_by_sku_returns_product_with_fiscal(client: TestClient, category: dict, supplier: dict):
    """Create with fiscal → GET by-sku returns same id with fiscal data."""
    response = client.post(
        "/products/",
        json={
            "name": "Feijão 1kg",
            "sku": "FEI-001",
            "barcode": "7890000000001",
            "sale_price": "8.90",
            "cost_price": "5.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
            "fiscal": {
                "ncm": "07133310",
                "cfop_default": "5102",
                "origem_produto": 0,
            },
        },
    )
    assert response.status_code == 201
    created_id = response.json()["id"]

    response = client.get("/products/by-sku/FEI-001")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created_id
    assert data["fiscal"]["ncm"] == "07133310"


def test_get_by_sku_not_found_returns_404(client: TestClient):
    """GET by-sku with non-existent SKU returns 404."""
    response = client.get("/products/by-sku/SKU-INEXISTENTE")
    assert response.status_code == 404


def test_get_by_barcode(client: TestClient, category: dict, supplier: dict):
    """GET by-barcode returns the correct product."""
    client.post(
        "/products/",
        json={
            "name": "Leite 1L",
            "sku": "LEI-001",
            "barcode": "7891111111111",
            "sale_price": "5.50",
            "cost_price": "3.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
        },
    )
    response = client.get("/products/by-barcode/7891111111111")
    assert response.status_code == 200
    assert response.json()["sku"] == "LEI-001"


def test_get_by_barcode_not_found_returns_404(client: TestClient):
    """GET by-barcode with non-existent barcode returns 404."""
    response = client.get("/products/by-barcode/0000000000000")
    assert response.status_code == 404


def test_duplicate_sku_returns_409(client: TestClient, category: dict, supplier: dict):
    """Replay same SKU on create → 409 ConflictException."""
    payload = {
        "name": "Produto Alfa",
        "sku": "SKU-DUPLO",
        "sale_price": "10.00",
        "cost_price": "5.00",
        "category_id": category["id"],
        "primary_supplier_id": supplier["id"],
    }
    assert client.post("/products/", json=payload).status_code == 201
    response = client.post("/products/", json={**payload, "name": "Produto Beta"})
    assert response.status_code == 409
    assert "sku" in response.json()["detail"].lower()


def test_duplicate_barcode_returns_409(client: TestClient, category: dict, supplier: dict):
    """Two products with same barcode → 409 on second create."""
    client.post(
        "/products/",
        json={
            "name": "Produto BC1",
            "sku": "BC-001",
            "barcode": "7899999999991",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
        },
    )
    response = client.post(
        "/products/",
        json={
            "name": "Produto BC2",
            "sku": "BC-002",
            "barcode": "7899999999991",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
        },
    )
    assert response.status_code == 409
    detail = response.json()["detail"].lower()
    assert "barcode" in detail or "código de barras" in detail or "ean" in detail


def test_invalid_ncm_returns_422(client: TestClient, category: dict, supplier: dict):
    """NCM with wrong digit count → 422."""
    response = client.post(
        "/products/",
        json={
            "name": "NCM Inválido",
            "sku": "NCM-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
            "fiscal": {"ncm": "123", "cfop_default": "5102", "origem_produto": 0},
        },
    )
    assert response.status_code == 422


def test_invalid_cfop_returns_422(client: TestClient, category: dict, supplier: dict):
    """CFOP with wrong digit count → 422."""
    response = client.post(
        "/products/",
        json={
            "name": "CFOP Inválido",
            "sku": "CFOP-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
            "fiscal": {"ncm": "10063021", "cfop_default": "51", "origem_produto": 0},
        },
    )
    assert response.status_code == 422


def test_invalid_cest_returns_422(client: TestClient, category: dict, supplier: dict):
    """CEST with wrong digit count → 422."""
    response = client.post(
        "/products/",
        json={
            "name": "CEST Inválido",
            "sku": "CEST-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
            "fiscal": {
                "ncm": "10063021",
                "cfop_default": "5102",
                "cest": "123",
                "origem_produto": 0,
            },
        },
    )
    assert response.status_code == 422


def test_invalid_origem_produto_returns_422(client: TestClient, category: dict, supplier: dict):
    """origem_produto out of 0–8 range → 422."""
    response = client.post(
        "/products/",
        json={
            "name": "Origem Inválida",
            "sku": "ORIG-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
            "fiscal": {"ncm": "10063021", "cfop_default": "5102", "origem_produto": 9},
        },
    )
    assert response.status_code == 422


def test_valid_fiscal_saves(client: TestClient, category: dict, supplier: dict):
    """Valid fiscal payload (with CEST) is persisted and returned."""
    response = client.post(
        "/products/",
        json={
            "name": "Produto Fiscal",
            "sku": "FIS-001",
            "barcode": "7894444444444",
            "sale_price": "30.00",
            "cost_price": "15.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
            "fiscal": {
                "ncm": "84713012",
                "cfop_default": "6102",
                "cest": "2140100",
                "origem_produto": 1,
            },
        },
    )
    assert response.status_code == 201
    fiscal = response.json()["fiscal"]
    assert fiscal["ncm"] == "84713012"
    assert fiscal["cfop_default"] == "6102"
    assert fiscal["cest"] == "2140100"
    assert fiscal["origem_produto"] == 1


def test_list_filter_by_q(client: TestClient, category: dict, supplier: dict):
    """List filter ?q= matches name and sku (ilike)."""
    client.post(
        "/products/",
        json={
            "name": "Notebook Dell",
            "sku": "NOTE-DELL",
            "sale_price": "3000.00",
            "cost_price": "2000.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
        },
    )
    client.post(
        "/products/",
        json={
            "name": "Monitor Samsung",
            "sku": "MON-SAMS",
            "sale_price": "1500.00",
            "cost_price": "1000.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
        },
    )
    response = client.get("/products/?q=dell")
    assert response.status_code == 200
    items = response.json()["items"]
    names = [i["name"] for i in items]
    assert "Notebook Dell" in names
    assert "Monitor Samsung" not in names


def test_list_filter_by_sku(client: TestClient, category: dict, supplier: dict):
    """List filter ?sku= exact match."""
    client.post(
        "/products/",
        json={
            "name": "Teclado Logitech",
            "sku": "TEC-LOG",
            "sale_price": "200.00",
            "cost_price": "100.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
        },
    )
    response = client.get("/products/?sku=TEC-LOG")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["sku"] == "TEC-LOG"


def test_list_filter_by_category_id(client: TestClient, category: dict, supplier: dict):
    """List filter ?category_id= returns only products from that category."""
    cat2 = client.post(
        "/categories/",
        json={"name": "Móveis", "slug": "moveis"},
    ).json()

    client.post(
        "/products/",
        json={
            "name": "Cadeira",
            "sku": "CAD-001",
            "sale_price": "500.00",
            "cost_price": "300.00",
            "category_id": cat2["id"],
            "primary_supplier_id": supplier["id"],
        },
    )
    client.post(
        "/products/",
        json={
            "name": "Mesa",
            "sku": "MES-001",
            "sale_price": "800.00",
            "cost_price": "500.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
        },
    )
    response = client.get(f"/products/?category_id={cat2['id']}")
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(i["category_id"] == cat2["id"] for i in items)
    assert any(i["name"] == "Cadeira" for i in items)


def test_list_filter_by_is_active(client: TestClient, category: dict, supplier: dict):
    """List filter ?is_active= filters by active status."""
    client.post(
        "/products/",
        json={
            "name": "Produto Ativo",
            "sku": "ATIVO-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
            "is_active": True,
        },
    )
    client.post(
        "/products/",
        json={
            "name": "Produto Inativo",
            "sku": "INATIVO-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
            "is_active": False,
        },
    )
    response = client.get("/products/?is_active=false")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    assert all(i["is_active"] is False for i in items)


# --- Épico 1: Produto deve usar categoria folha ---


def test_create_product_on_leaf_subcategory_returns_201(client: TestClient, supplier: dict):
    root = client.post(
        "/categories/",
        json={"name": "Raiz Produto", "slug": "raiz-produto", "is_active": True},
    ).json()
    sub = client.post(
        "/categories/",
        json={
            "name": "Sub Produto",
            "slug": "sub-produto",
            "is_active": True,
            "parent_id": root["id"],
        },
    ).json()

    response = client.post(
        "/products/",
        json={
            "name": "Produto em Subcategoria",
            "sku": "PROD-LEAF-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": sub["id"],
            "primary_supplier_id": supplier["id"],
        },
    )
    assert response.status_code == 201


def test_create_product_on_root_with_no_children_returns_201(client: TestClient, supplier: dict):
    root = client.post(
        "/categories/",
        json={"name": "Raiz Sem Filhos", "slug": "raiz-sem-filhos", "is_active": True},
    ).json()

    response = client.post(
        "/products/",
        json={
            "name": "Produto em Raiz Sem Filhos",
            "sku": "PROD-ROOT-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": root["id"],
            "primary_supplier_id": supplier["id"],
        },
    )
    assert response.status_code == 201


def test_create_product_on_root_with_children_returns_422(client: TestClient, supplier: dict):
    root = client.post(
        "/categories/",
        json={"name": "Raiz Com Filhos", "slug": "raiz-com-filhos", "is_active": True},
    ).json()
    client.post(
        "/categories/",
        json={"name": "Filho1", "slug": "filho1-prod", "is_active": True, "parent_id": root["id"]},
    )

    response = client.post(
        "/products/",
        json={
            "name": "Produto na Raiz",
            "sku": "PROD-NONLEAF-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": root["id"],
            "primary_supplier_id": supplier["id"],
        },
    )
    assert response.status_code == 422


def test_update_product_category_to_root_with_children_returns_422(
    client: TestClient, category: dict, supplier: dict
):
    root = client.post(
        "/categories/",
        json={"name": "Raiz Bloqueada", "slug": "raiz-bloqueada", "is_active": True},
    ).json()
    client.post(
        "/categories/",
        json={
            "name": "Filho Raiz",
            "slug": "filho-raiz",
            "is_active": True,
            "parent_id": root["id"],
        },
    )
    product = client.post(
        "/products/",
        json={
            "name": "Produto Para Mover",
            "sku": "PROD-MOVE-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": category["id"],
            "primary_supplier_id": supplier["id"],
        },
    ).json()

    response = client.put(
        f"/products/{product['id']}",
        json={"category_id": root["id"]},
    )
    assert response.status_code == 422
