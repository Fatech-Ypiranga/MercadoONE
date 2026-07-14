from fastapi.testclient import TestClient

from tests.conftest import page_items


def test_admin_creates_user(client: TestClient):
    response = client.post(
        "/users/",
        json={
            "full_name": "Novo Operador",
            "cpf": "55555555555",
            "email": "novo@test.local",
            "username": "novo_operador",
            "password": "senha123",
            "profile": "operador",
            "is_active": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["profile"] == "operador"
    assert data["username"] == "novo_operador"


def test_admin_lists_users(client: TestClient):
    response = client.get("/users/")
    assert response.status_code == 200
    assert len(page_items(response)) >= 1


def test_admin_resets_user_password(client: TestClient):
    create = client.post(
        "/users/",
        json={
            "full_name": "Reset Target",
            "cpf": "66666666666",
            "email": "reset@test.local",
            "username": "reset_user",
            "password": "oldpass1",
            "profile": "colaborador",
            "is_active": True,
        },
    )
    user_id = create.json()["id"]

    response = client.patch(f"/users/{user_id}/password", json={"new_password": "newpass1"})
    assert response.status_code == 200

    login = client.post("/auth/login", json={"login": "reset_user", "password": "newpass1"})
    assert login.status_code == 200


def test_admin_hard_deletes_user(client: TestClient):
    create = client.post(
        "/users/",
        json={
            "full_name": "To Delete",
            "cpf": "77777777777",
            "email": "delete@test.local",
            "username": "delete_user",
            "password": "delpass1",
            "profile": "colaborador",
            "is_active": True,
        },
    )
    user_id = create.json()["id"]

    response = client.delete(f"/users/{user_id}")
    assert response.status_code == 204

    detail = client.get(f"/users/{user_id}")
    assert detail.status_code == 404

    login = client.post("/auth/login", json={"login": "delete_user", "password": "delpass1"})
    assert login.status_code == 401


def test_admin_gets_user_by_id(client: TestClient):
    me = client.get("/auth/me").json()
    response = client.get(f"/users/{me['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == me["id"]
    assert response.json()["username"] == me["username"]


def test_admin_updates_user(client: TestClient):
    create = client.post(
        "/users/",
        json={
            "full_name": "Update Target",
            "cpf": "88888888888",
            "email": "update@test.local",
            "username": "update_user",
            "password": "uppass12",
            "profile": "colaborador",
            "is_active": True,
        },
    )
    user_id = create.json()["id"]

    response = client.put(
        f"/users/{user_id}",
        json={"full_name": "Nome Atualizado", "profile": "operador"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Nome Atualizado"
    assert response.json()["profile"] == "operador"


def test_admin_cannot_deactivate_self(client: TestClient):
    me = client.get("/auth/me").json()
    response = client.delete(f"/users/{me['id']}")
    assert response.status_code == 422
    assert "own account" in response.json()["detail"]
