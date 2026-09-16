from fastapi import APIRouter, Depends

from cep.models import CepResponse
from cep.service import CepService
from shared.identity.dependencies import get_current_user
from users.models import User

router = APIRouter(prefix="/cep", tags=["CEP"])


@router.get("/{cep}", response_model=CepResponse, summary="Consultar endereço por CEP")
async def get_cep(
    cep: str,
    current_user: User = Depends(get_current_user),
):
    return await CepService.lookup(cep)
