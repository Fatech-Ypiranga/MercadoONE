"""Tests for GET /cep/{cep} endpoint — TDD (written before implementation)."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_CEP = "01310100"  # Av. Paulista, SP
VIACEP_SUCCESS = {
    "cep": "01310-100",
    "logradouro": "Avenida Paulista",
    "complemento": "de 1 a 610 - lado par",
    "bairro": "Bela Vista",
    "localidade": "São Paulo",
    "uf": "SP",
    "ibge": "3550308",
    "gia": "1004",
    "ddd": "11",
    "siafi": "7107",
}

VIACEP_NOT_FOUND = {"erro": True}


def _mock_httpx_response(json_data: dict, status_code: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------


def test_cep_requires_auth():
    """Endpoint must reject unauthenticated requests with 401."""
    from main import create_app

    app = create_app(init_database=False, validate_config=False)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(f"/cep/{VALID_CEP}")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Valid CEP
# ---------------------------------------------------------------------------


def test_cep_valid_returns_mapped_fields(client: TestClient):
    """Valid 8-digit CEP → 200 with all mapped fields including ibge_code."""
    with patch("cep.service.httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(return_value=_mock_httpx_response(VIACEP_SUCCESS))

        response = client.get(f"/cep/{VALID_CEP}")

    assert response.status_code == 200
    data = response.json()
    assert data["zip_code"] == VALID_CEP
    assert data["street"] == "Avenida Paulista"
    assert data["neighborhood"] == "Bela Vista"
    assert data["city"] == "São Paulo"
    assert data["state"] == "SP"
    assert data["ibge_code"] == "3550308"


def test_cep_with_mask_is_normalized(client: TestClient):
    """CEP passed as 01310-100 (with dash) must be normalized before lookup."""
    with patch("cep.service.httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(return_value=_mock_httpx_response(VIACEP_SUCCESS))

        response = client.get("/cep/01310-100")

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Invalid format
# ---------------------------------------------------------------------------


def test_cep_short_returns_422(client: TestClient):
    """CEP with fewer than 8 digits → 422 Unprocessable Entity."""
    response = client.get("/cep/1234567")
    assert response.status_code == 422


def test_cep_non_digits_only_returns_422(client: TestClient):
    """CEP that yields fewer than 8 digits after stripping → 422."""
    response = client.get("/cep/ABCDEFGH")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# ViaCEP "erro: true" — CEP not found
# ---------------------------------------------------------------------------


def test_cep_not_found_returns_404(client: TestClient):
    """ViaCEP returns {erro: true} → 404 with descriptive message."""
    with patch("cep.service.httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(return_value=_mock_httpx_response(VIACEP_NOT_FOUND))

        response = client.get(f"/cep/{VALID_CEP}")

    assert response.status_code == 404
    assert "CEP" in response.json()["detail"] or "cep" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Network / timeout errors → 502/503
# ---------------------------------------------------------------------------


def test_cep_timeout_returns_502_or_503(client: TestClient):
    """Timeout when calling ViaCEP → 502 or 503, not 500."""
    import httpx as real_httpx

    with patch("cep.service.httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(side_effect=real_httpx.TimeoutException("timeout"))

        response = client.get(f"/cep/{VALID_CEP}")

    assert response.status_code in (502, 503)
    body = response.json()
    assert "detail" in body
    # Message must be user-friendly, not a raw traceback
    assert len(body["detail"]) < 300


def test_cep_network_error_returns_502_or_503(client: TestClient):
    """General network failure → 502 or 503, not 500."""
    import httpx as real_httpx

    with patch("cep.service.httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(side_effect=real_httpx.ConnectError("connection refused"))

        response = client.get(f"/cep/{VALID_CEP}")

    assert response.status_code in (502, 503)
