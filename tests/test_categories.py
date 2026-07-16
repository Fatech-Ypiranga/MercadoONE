from fastapi.testclient import TestClient


def test_create_category(client: TestClient):
    response = client.post(
        "/categories/",
        json={"name": "Bebidas", "slug": "bebidas", "is_active": True},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Bebidas"
    assert data["slug"] == "bebidas"


def test_get_category_detail(client: TestClient, category: dict):
    response = client.get(f"/categories/{category['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == category["id"]
    assert "products" in response.json()


def test_update_category(client: TestClient, category: dict):
    response = client.put(
        f"/categories/{category['id']}",
        json={"name": "Eletrônicos Premium"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Eletrônicos Premium"


def test_delete_empty_category(client: TestClient):
    created = client.post(
        "/categories/",
        json={"name": "Vazia", "slug": "vazia", "is_active": True},
    ).json()
    response = client.delete(f"/categories/{created['id']}")
    assert response.status_code == 204


def test_delete_category_with_products_returns_409(
    client: TestClient, category: dict, product: dict
):
    response = client.delete(f"/categories/{category['id']}")
    assert response.status_code == 409
    assert "produtos vinculados" in response.json()["detail"]


def test_get_nonexistent_category_returns_404(client: TestClient):
    response = client.get("/categories/99999")
    assert response.status_code == 404


def test_colaborador_cannot_create_category(colaborador_client: TestClient):
    response = colaborador_client.post(
        "/categories/",
        json={"name": "Bloqueada", "slug": "bloqueada", "is_active": True},
    )
    assert response.status_code == 403


def test_gerente_can_create_category(gerente_client: TestClient):
    response = gerente_client.post(
        "/categories/",
        json={"name": "Gerente Cat", "slug": "gerente-cat", "is_active": True},
    )
    assert response.status_code == 201


# --- Épico 1: Categoria (API) ---


def test_get_category_by_slug(client: TestClient):
    created = client.post(
        "/categories/",
        json={"name": "Ferramentas", "slug": "ferramentas", "is_active": True},
    ).json()

    response = client.get("/categories/by-slug/ferramentas")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created["id"]
    assert data["slug"] == "ferramentas"


def test_get_category_by_slug_not_found(client: TestClient):
    response = client.get("/categories/by-slug/slug-inexistente")
    assert response.status_code == 404


def test_create_duplicate_slug_returns_409(client: TestClient):
    client.post(
        "/categories/",
        json={"name": "Original", "slug": "duplicado", "is_active": True},
    )
    response = client.post(
        "/categories/",
        json={"name": "Outra", "slug": "duplicado", "is_active": True},
    )
    assert response.status_code == 409
    assert "slug" in response.json()["detail"].lower()


def test_update_to_existing_slug_returns_409(client: TestClient):
    cat_a = client.post(
        "/categories/",
        json={"name": "Categoria A", "slug": "slug-a", "is_active": True},
    ).json()
    client.post(
        "/categories/",
        json={"name": "Categoria B", "slug": "slug-b", "is_active": True},
    )

    response = client.put(f"/categories/{cat_a['id']}", json={"slug": "slug-b"})
    assert response.status_code == 409
    assert "slug" in response.json()["detail"].lower()


def test_list_categories_filter_by_q(client: TestClient):
    client.post("/categories/", json={"name": "Smartphones", "slug": "smartphones"})
    client.post("/categories/", json={"name": "Tablets", "slug": "tablets"})

    response = client.get("/categories/?q=smart")
    assert response.status_code == 200
    items = response.json()["items"]
    assert all("smart" in (i["name"] + i["slug"]).lower() for i in items)
    names = [i["name"] for i in items]
    assert "Smartphones" in names
    assert "Tablets" not in names


def test_list_categories_filter_by_is_active(client: TestClient):
    client.post("/categories/", json={"name": "Ativa", "slug": "ativa", "is_active": True})
    client.post("/categories/", json={"name": "Inativa", "slug": "inativa", "is_active": False})

    response = client.get("/categories/?is_active=true")
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(i["is_active"] is True for i in items)

    response_inactive = client.get("/categories/?is_active=false")
    items_inactive = response_inactive.json()["items"]
    assert all(i["is_active"] is False for i in items_inactive)
