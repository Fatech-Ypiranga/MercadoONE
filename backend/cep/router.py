from fastapi import APIRouter, Depends

from cep.models import CepResponse
from cep.service import CepService
from models.user import User
from shared.identity.dependencies import get_current_user

router = APIRouter(prefix="/cep", tags=["CEP"])


@router.get("/{cep}", response_model=CepResponse, summary="Consultar endereço por CEP")
async def get_cep(
    cep: str,
    current_user: User = Depends(get_current_user),
):
    return await CepService.lookup(cep)
