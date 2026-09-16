"""Branch/store delete previously had no dependency check at all (unlike
categories/products/suppliers/users), so deleting one with stores/users/
sales/purchases/stock attached raised a raw FK-violation IntegrityError
that leaked as a 400 with the SQL statement in the message. See
docs/ROADMAP.md DB-02.
"""

from fastapi.testclient import TestClient


def test_delete_branch_with_store_and_user_returns_409(client: TestClient):
    me = client.get("/auth/me").json()
    branch_id = me["default_branch"]["id"]

    response = client.delete(f"/branches/{branch_id}")
    assert response.status_code == 409
    assert "sql" not in response.json()["detail"].lower()
    assert "select" not in response.json()["detail"].lower()


def test_delete_store_with_user_returns_409(client: TestClient):
    me = client.get("/auth/me").json()
    store_id = me["default_store"]["id"]

    response = client.delete(f"/stores/{store_id}")
    assert response.status_code == 409
    assert "sql" not in response.json()["detail"].lower()
    assert "select" not in response.json()["detail"].lower()
