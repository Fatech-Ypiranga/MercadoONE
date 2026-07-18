from fastapi import APIRouter, Depends

from auth.dependencies import get_current_user
from models.cep import CepResponse
from models.user import User
from services.cep_service import CepService

router = APIRouter(prefix="/cep", tags=["CEP"])


@router.get("/{cep}", response_model=CepResponse, summary="Consultar endereço por CEP")
async def get_cep(
    cep: str,
    current_user: User = Depends(get_current_user),
):
    return await CepService.lookup(cep)
