from fastapi.testclient import TestClient

from tests.conftest import page_items


def test_create_brand(client: TestClient):
    response = client.post("/brands/", json={"name": "Marca Teste"})
    assert response.status_code == 201
    assert response.json()["name"] == "Marca Teste"


def test_list_and_get_brand(client: TestClient):
    created = client.post("/brands/", json={"name": "Outra Marca"}).json()
    listing = client.get("/brands/")
    assert listing.status_code == 200
    assert any(b["id"] == created["id"] for b in page_items(listing))

    detail = client.get(f"/brands/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "Outra Marca"


def test_update_brand(client: TestClient):
    created = client.post("/brands/", json={"name": "Antiga"}).json()
    response = client.put(f"/brands/{created['id']}", json={"name": "Nova"})
    assert response.status_code == 200
    assert response.json()["name"] == "Nova"


def test_delete_brand(client: TestClient):
    created = client.post("/brands/", json={"name": "Para Deletar"}).json()
    response = client.delete(f"/brands/{created['id']}")
    assert response.status_code == 204

    detail = client.get(f"/brands/{created['id']}")
    assert detail.status_code == 404


def test_delete_brand_with_products_returns_409(client: TestClient, category: dict):
    brand = client.post("/brands/", json={"name": "Com Produto"}).json()
    client.post(
        "/products/",
        json={
            "name": "Produto com Marca",
            "sku": "BRD-001",
            "sale_price": "10.00",
            "cost_price": "5.00",
            "category_id": category["id"],
            "brand_id": brand["id"],
        },
    )
    response = client.delete(f"/brands/{brand['id']}")
    assert response.status_code == 409
    assert "produtos vinculados" in response.json()["detail"]


def test_get_nonexistent_brand_returns_404(client: TestClient):
    response = client.get("/brands/99999")
    assert response.status_code == 404


def test_colaborador_cannot_create_brand(colaborador_client: TestClient):
    response = colaborador_client.post("/brands/", json={"name": "Bloqueada"})
    assert response.status_code == 403


def test_gerente_can_create_brand(gerente_client: TestClient):
    response = gerente_client.post("/brands/", json={"name": "Gerente Brand"})
    assert response.status_code == 201
