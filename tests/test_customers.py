from fastapi.testclient import TestClient

from utils.cpf import build_cpf


def _customer_payload(**overrides) -> dict:
    payload = {
        "name": "João Silva",
        "email": "joao@cliente.fake",
        "phone": "11999998888",
        "customer_type": "F",
        "document": build_cpf(501),
        "is_active": True,
        "addresses": [
            {
                "description": "Principal",
                "zip_code": "01310100",
                "street": "Av. Paulista",
                "number": "1000",
                "neighborhood": "Bela Vista",
                "city": "São Paulo",
                "state": "SP",
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_create_customer_with_address(client: TestClient):
    response = client.post("/customers/", json=_customer_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "João Silva"
    assert data["document"] == build_cpf(501)
    assert len(data["addresses"]) == 1
    assert data["addresses"][0]["city"] == "São Paulo"


def test_get_customer_detail(client: TestClient):
    created = client.post("/customers/", json=_customer_payload(document=build_cpf(502))).json()
    response = client.get(f"/customers/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert len(response.json()["addresses"]) == 1


def test_update_customer(client: TestClient):
    created = client.post("/customers/", json=_customer_payload(document=build_cpf(503))).json()
    response = client.put(
        f"/customers/{created['id']}",
        json={"name": "João Silva Atualizado", "phone": "11888887777"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "João Silva Atualizado"


def test_customer_address_crud(client: TestClient):
    created = client.post("/customers/", json=_customer_payload(document=build_cpf(504))).json()
    customer_id = created["id"]

    add = client.post(
        f"/customers/{customer_id}/addresses",
        json={
            "description": "Entrega",
            "zip_code": "04538133",
            "street": "Av. Brigadeiro Faria Lima",
            "number": "2000",
            "neighborhood": "Itaim Bibi",
            "city": "São Paulo",
            "state": "SP",
        },
    )
    assert add.status_code == 201
    address_id = add.json()["id"]

    update = client.put(
        f"/customers/{customer_id}/addresses/{address_id}",
        json={"description": "Entrega atualizada"},
    )
    assert update.status_code == 200
    assert update.json()["description"] == "Entrega atualizada"

    delete = client.delete(f"/customers/{customer_id}/addresses/{address_id}")
    assert delete.status_code == 204


def test_get_nonexistent_customer_returns_404(client: TestClient):
    response = client.get("/customers/99999")
    assert response.status_code == 404


def test_operador_can_create_customer(operador_client: TestClient):
    response = operador_client.post(
        "/customers/",
        json=_customer_payload(document=build_cpf(505), email="operador@cliente.fake"),
    )
    assert response.status_code == 201


def test_colaborador_cannot_create_customer(colaborador_client: TestClient):
    response = colaborador_client.post(
        "/customers/",
        json=_customer_payload(document=build_cpf(506), email="colab@cliente.fake"),
    )
    assert response.status_code == 403


def test_invalid_cpf_rejected(client: TestClient):
    response = client.post("/customers/", json=_customer_payload(document="12345678901"))
    assert response.status_code == 422
