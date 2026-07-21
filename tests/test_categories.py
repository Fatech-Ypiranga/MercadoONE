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


# --- Épico 1: Subcategorias (1 nível) ---


def test_create_subcategory_under_root(client: TestClient):
    root = client.post(
        "/categories/",
        json={"name": "Eletrônicos", "slug": "eletronicos", "is_active": True},
    ).json()

    response = client.post(
        "/categories/",
        json={"name": "Celulares", "slug": "celulares", "is_active": True, "parent_id": root["id"]},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["parent_id"] == root["id"]


def test_create_subcategory_under_missing_parent_returns_404(client: TestClient):
    response = client.post(
        "/categories/",
        json={"name": "Orphan", "slug": "orphan", "is_active": True, "parent_id": 99999},
    )
    assert response.status_code == 404


def test_create_subcategory_under_subcategory_returns_422(client: TestClient):
    root = client.post(
        "/categories/",
        json={"name": "Raiz", "slug": "raiz", "is_active": True},
    ).json()
    sub = client.post(
        "/categories/",
        json={"name": "Sub", "slug": "sub", "is_active": True, "parent_id": root["id"]},
    ).json()

    response = client.post(
        "/categories/",
        json={"name": "SubSub", "slug": "subsub", "is_active": True, "parent_id": sub["id"]},
    )
    assert response.status_code == 422


def test_delete_root_with_children_returns_409(client: TestClient):
    root = client.post(
        "/categories/",
        json={"name": "Pai", "slug": "pai", "is_active": True},
    ).json()
    client.post(
        "/categories/",
        json={"name": "Filho", "slug": "filho", "is_active": True, "parent_id": root["id"]},
    )

    response = client.delete(f"/categories/{root['id']}")
    assert response.status_code == 409
    assert "subcategoria" in response.json()["detail"].lower()


def test_update_parent_id_to_self_returns_422(client: TestClient):
    root = client.post(
        "/categories/",
        json={"name": "AutoRef", "slug": "autoref", "is_active": True},
    ).json()

    response = client.put(
        f"/categories/{root['id']}",
        json={"parent_id": root["id"]},
    )
    assert response.status_code == 422


def test_update_parent_id_on_category_with_children_returns_422(client: TestClient):
    root_a = client.post(
        "/categories/",
        json={"name": "RaizA", "slug": "raiz-a", "is_active": True},
    ).json()
    root_b = client.post(
        "/categories/",
        json={"name": "RaizB", "slug": "raiz-b", "is_active": True},
    ).json()
    client.post(
        "/categories/",
        json={"name": "FilhoA", "slug": "filho-a", "is_active": True, "parent_id": root_a["id"]},
    )

    response = client.put(
        f"/categories/{root_a['id']}",
        json={"parent_id": root_b["id"]},
    )
    assert response.status_code == 422


def test_tenant_isolation_cannot_use_other_company_parent(
    client: TestClient, second_company_client: TestClient
):
    root = client.post(
        "/categories/",
        json={"name": "RaizEmpresa1", "slug": "raiz-empresa-1", "is_active": True},
    ).json()

    response = second_company_client.post(
        "/categories/",
        json={"name": "Sub", "slug": "sub-empresa-2", "is_active": True, "parent_id": root["id"]},
    )
    assert response.status_code == 404


def test_list_categories_filter_by_parent_id(client: TestClient):
    root = client.post(
        "/categories/",
        json={"name": "PaiFilter", "slug": "pai-filter", "is_active": True},
    ).json()
    client.post(
        "/categories/",
        json={
            "name": "FilhoFilter",
            "slug": "filho-filter",
            "is_active": True,
            "parent_id": root["id"],
        },
    )
    client.post(
        "/categories/",
        json={"name": "OutraCat", "slug": "outra-cat", "is_active": True},
    )

    response = client.get(f"/categories/?parent_id={root['id']}")
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(i["parent_id"] == root["id"] for i in items)
    assert len(items) >= 1
    assert any(i["name"] == "FilhoFilter" for i in items)
