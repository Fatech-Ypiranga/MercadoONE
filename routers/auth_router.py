from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from auth.dependencies import get_current_user
from database.connection import get_db
from models.user import MeBranchInfo, MeCompanyInfo, MeResponse, MeStoreInfo, User
from repositories.company_repository import BranchRepository, CompanyRepository, StoreRepository
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticação"])


class LoginRequest(BaseModel):
    login: str = Field(description="E-mail ou nome de usuário")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


@router.post("/login", response_model=TokenResponse, summary="Autenticar e obter token JWT")
def login(login_in: LoginRequest, db: Session = Depends(get_db)):
    return AuthService(db).login(login_in.login, login_in.password)


@router.get("/me", response_model=MeResponse, summary="Obter usuário autenticado")
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    company = CompanyRepository.find_by_id(db, current_user.company_id)
    branch = None
    store = None
    if current_user.default_branch_id:
        branch = BranchRepository.find_by_id_for_company(
            db, current_user.default_branch_id, current_user.company_id
        )
    if current_user.default_store_id:
        store = StoreRepository.find_by_id_for_company(
            db, current_user.default_store_id, current_user.company_id
        )

    data = MeResponse.model_validate(current_user)
    if company:
        data.company = MeCompanyInfo(
            id=company.id,
            legal_name=company.legal_name,
            trade_name=company.trade_name,
            document=company.document,
        )
    if branch:
        data.default_branch = MeBranchInfo(
            id=branch.id,
            name=branch.name,
            code=branch.code,
        )
    if store:
        data.default_store = MeStoreInfo(
            id=store.id,
            name=store.name,
            code=store.code,
            branch_id=store.branch_id,
        )
    return data


@router.post(
    "/change-password", status_code=status.HTTP_204_NO_CONTENT, summary="Alterar própria senha"
)
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ip_address = request.client.host if request.client else None
    AuthService(db).change_password(
        current_user,
        current_password=body.current_password,
        new_password=body.new_password,
        ip_address=ip_address,
    )
