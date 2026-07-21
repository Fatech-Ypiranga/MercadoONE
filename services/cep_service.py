import httpx

from models.cep import CepResponse
from services.exceptions import ExternalServiceException, ResourceNotFoundException, ValidationError

VIACEP_URL = "https://viacep.com.br/ws/{cep}/json/"
TIMEOUT = 5.0


class CepService:
    @staticmethod
    def _normalize(raw_cep: str) -> str:
        digits = "".join(ch for ch in raw_cep if ch.isdigit())
        if len(digits) != 8:
            raise ValidationError(f"CEP inválido: '{raw_cep}'. Informe exatamente 8 dígitos.")
        return digits

    @staticmethod
    async def lookup(raw_cep: str) -> CepResponse:
        cep = CepService._normalize(raw_cep)

        try:
            # Force IPv4: ViaCEP publishes AAAA; Railway egress can fail on IPv6.
            transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
            async with httpx.AsyncClient(timeout=TIMEOUT, transport=transport) as client:
                response = await client.get(VIACEP_URL.format(cep=cep))
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise ExternalServiceException(
                "Serviço de CEP indisponível: tempo de resposta excedido. "
                "Preencha o endereço manualmente.",
                status_code=503,
            ) from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceException(
                "Não foi possível consultar o serviço de CEP. Preencha o endereço manualmente.",
                status_code=502,
            ) from exc
        except ValueError as exc:
            raise ExternalServiceException(
                "Resposta inválida do serviço de CEP. Preencha o endereço manualmente.",
                status_code=502,
            ) from exc

        if data.get("erro"):
            raise ResourceNotFoundException(f"CEP '{cep}' não encontrado.")

        return CepResponse(
            zip_code=cep,
            street=data.get("logradouro", "") or "",
            neighborhood=data.get("bairro", "") or "",
            city=data.get("localidade", "") or "",
            state=data.get("uf", "") or "",
            ibge_code=data.get("ibge") or None,
        )
