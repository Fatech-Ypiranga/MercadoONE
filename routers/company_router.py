from fastapi import APIRouter, Depends
from sqlmodel import Session

from auth.dependencies import require_permission
from auth.scope import company_id_of
from database.connection import get_db
from models.company import CompanyResponse, CompanyUpdate
from models.user import User
from services.org_service import OrgService

router = APIRouter(prefix="/companies", tags=["Empresas"])


@router.get("/me", response_model=CompanyResponse, summary="Obter empresa do usuário autenticado")
def get_my_company(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("companies:read")),
):
    company_id = company_id_of(current_user)
    return OrgService(db).get_company(company_id)


@router.patch(
    "/me",
    response_model=CompanyResponse,
    summary="Atualizar empresa do usuário autenticado",
)
def update_my_company(
    company_in: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("companies:write")),
):
    company_id = company_id_of(current_user)
    return OrgService(db).update_company(
        company_id,
        company_in,
        actor_id=current_user.id,
    )
