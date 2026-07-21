from fastapi.testclient import TestClient

from database.seed import SEED_COMPANY_DOCUMENT
from models.user import User
from tests.conftest import page_items
from utils.cpf import build_cpf


def _login_payload(login: str, password: str) -> dict:
    return {
        "login": login,
        "password": password,
        "company_document": SEED_COMPANY_DOCUMENT,
    }


def test_admin_creates_user(client: TestClient):
    response = client.post(
        "/users/",
        json={
            "full_name": "Novo Operador",
            "cpf": build_cpf(201),
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
    assert data["pdv_id"] is not None
    assert len(data["pdv_id"]) == 6
    assert data["pdv_id"].isdigit()


def test_admin_lists_users(client: TestClient):
    response = client.get("/users/")
    assert response.status_code == 200
    assert len(page_items(response)) >= 1


def test_admin_filters_users(client: TestClient):
    client.post(
        "/users/",
        json={
            "full_name": "Filtro Operador",
            "cpf": build_cpf(202),
            "email": "filtro@test.local",
            "username": "filtro_op",
            "password": "senha123",
            "profile": "operador",
            "is_active": True,
        },
    )
    response = client.get("/users/", params={"profile": "operador", "q": "Filtro"})
    assert response.status_code == 200
    items = page_items(response)
    assert len(items) >= 1
    assert all(item["profile"] == "operador" for item in items)


def test_admin_resets_user_password(client: TestClient):
    create = client.post(
        "/users/",
        json={
            "full_name": "Reset Target",
            "cpf": build_cpf(203),
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

    login = client.post("/auth/login", json=_login_payload("reset_user", "newpass1"))
    assert login.status_code == 200


def test_admin_hard_deletes_user(client: TestClient):
    create = client.post(
        "/users/",
        json={
            "full_name": "To Delete",
            "cpf": build_cpf(204),
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

    login = client.post("/auth/login", json=_login_payload("delete_user", "delpass1"))
    assert login.status_code == 401


def test_admin_gets_user_by_id(client: TestClient):
    me = client.get("/auth/me").json()
    response = client.get(f"/users/{me['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == me["id"]
    assert response.json()["username"] == me["username"]
    assert response.json()["pdv_id"] is not None


def test_admin_updates_user(client: TestClient):
    create = client.post(
        "/users/",
        json={
            "full_name": "Update Target",
            "cpf": build_cpf(205),
            "email": "update@test.local",
            "username": "update_user",
            "password": "uppass12",
            "profile": "colaborador",
            "is_active": True,
        },
    )
    user_id = create.json()["id"]
    assert create.json()["pdv_id"] is None

    response = client.put(
        f"/users/{user_id}",
        json={"full_name": "Nome Atualizado", "profile": "operador"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Nome Atualizado"
    assert response.json()["profile"] == "operador"
    assert response.json()["pdv_id"] is not None


def test_admin_cannot_deactivate_self(client: TestClient):
    me = client.get("/auth/me").json()
    response = client.delete(f"/users/{me['id']}")
    assert response.status_code == 422
    assert "own account" in response.json()["detail"]


def test_invalid_cpf_rejected(client: TestClient):
    response = client.post(
        "/users/",
        json={
            "full_name": "CPF Invalido",
            "cpf": "11111111111",
            "email": "cpfbad@test.local",
            "username": "cpfbad",
            "password": "senha123",
            "profile": "colaborador",
            "is_active": True,
        },
    )
    assert response.status_code == 422


def test_admin_generates_supervisor_pdv_pin(client: TestClient, db_session):
    create = client.post(
        "/users/",
        json={
            "full_name": "Supervisor PIN",
            "cpf": build_cpf(206),
            "email": "suppin@test.local",
            "username": "suppin",
            "password": "senha123",
            "profile": "supervisor",
            "is_active": True,
        },
    )
    assert create.status_code == 201
    user = create.json()
    assert user["pdv_id"] is not None
    assert user["has_pdv_pin"] is False

    pin_response = client.post(f"/users/{user['id']}/pdv-pin")
    assert pin_response.status_code == 200
    body = pin_response.json()
    assert len(body["pdv_pin"]) == 12
    assert body["pdv_pin"].isdigit()
    assert body["pdv_id"] == user["pdv_id"]

    detail = client.get(f"/users/{user['id']}").json()
    assert detail["has_pdv_pin"] is True
    assert "pdv_pin" not in detail

    stored = db_session.get(User, user["id"])
    assert stored is not None
    assert stored.pdv_pin_hash is not None
    assert stored.pdv_pin_hash.startswith("$argon2id$")
    assert not stored.pdv_pin_hash.startswith("$2b$")


def test_operador_cannot_receive_pdv_pin(client: TestClient):
    create = client.post(
        "/users/",
        json={
            "full_name": "Operador Sem PIN",
            "cpf": build_cpf(207),
            "email": "opnopin@test.local",
            "username": "opnopin",
            "password": "senha123",
            "profile": "operador",
            "is_active": True,
        },
    )
    user_id = create.json()["id"]
    response = client.post(f"/users/{user_id}/pdv-pin")
    assert response.status_code == 422


def test_store_pdv_pin_returns_argon2id_hash_for_sync(client: TestClient, db_session):
    from auth.security import verify_pdv_pin
    from models.user import User

    me = client.get("/auth/me").json()
    admin = db_session.get(User, me["id"])
    assert admin is not None
    store_id = me["default_store_id"]
    assert store_id is not None

    pin_body = client.post(f"/users/{admin.id}/pdv-pin").json()
    pin = pin_body["pdv_pin"]
    db_session.expire_all()
    admin = db_session.get(User, me["id"])
    assert admin is not None
    assert admin.pdv_pin_hash is not None

    response = client.get(f"/stores/{store_id}/pdv-pin")
    assert response.status_code == 200
    body = response.json()
    assert body["store_id"] == store_id
    assert body["user_id"] == admin.id
    assert body["pin_hash"].startswith("$argon2id$")
    assert verify_pdv_pin(pin, body["pin_hash"]) is True


def test_store_pdv_pin_requires_existing_pin(client: TestClient, db_session):
    from models.user import User
    from tests.conftest import login, page_items

    create = client.post(
        "/users/",
        json={
            "full_name": "Supervisor Sem Sync PIN",
            "cpf": build_cpf(208),
            "email": "supnosync@test.local",
            "username": "supnosync",
            "password": "senha123",
            "profile": "supervisor",
            "is_active": True,
        },
    )
    assert create.status_code == 201
    user = create.json()

    stores = page_items(client.get("/stores/"))
    assert stores
    store_id = stores[0]["id"]

    token = login(client, "supnosync", "senha123")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/stores/{store_id}/pdv-pin", headers=headers)
    assert response.status_code == 422
    assert "No PDV PIN" in response.json()["detail"]

    stored = db_session.get(User, user["id"])
    assert stored is not None
    assert stored.pdv_pin_hash is None
