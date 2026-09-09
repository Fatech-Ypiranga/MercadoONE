from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from auth.service import AuthService
from database.connection import get_db
from middleware.security import resolve_client_ip
from models.user import MeBranchInfo, MeCompanyInfo, MeResponse, MeStoreInfo, User
from organization.repository import BranchRepository, CompanyRepository, StoreRepository
from services.user_service import to_user_response
from shared.identity.dependencies import get_current_user, require_permission

router = APIRouter(prefix="/auth", tags=["Autenticação"])


class LoginRequest(BaseModel):
    login: str = Field(description="E-mail ou nome de usuário")
    password: str
    company_document: str = Field(description="CNPJ da empresa (com ou sem pontuação)")


class PdvLoginRequest(BaseModel):
    company_document: str
    pdv_id: str = Field(description="ID de PDV com 6 dígitos")
    password: str = Field(description="Senha de login do usuário")


class PdvAuthorizeRequest(BaseModel):
    pdv_id: str = Field(description="ID de PDV do Supervisor+")
    pin: str = Field(description="PIN numérico de 12 dígitos")
    actions: list[str] = Field(description="Ações a autorizar: discount, cancel")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class PdvAuthorizeResponse(BaseModel):
    authorization_token: str
    token_type: str
    expires_in: int
    actions: list[str]
    supervisor_user_id: int
    supervisor_pdv_id: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


@router.post("/login", response_model=TokenResponse, summary="Autenticar e obter token JWT")
def login(login_in: LoginRequest, db: Session = Depends(get_db)):
    return AuthService(db).login(
        login_in.login,
        login_in.password,
        company_document=login_in.company_document,
    )


@router.post(
    "/pdv-login",
    response_model=TokenResponse,
    summary="Autenticar no PDV por ID de PDV + senha de login",
)
def pdv_login(body: PdvLoginRequest, db: Session = Depends(get_db)):
    return AuthService(db).pdv_login(
        company_document=body.company_document,
        pdv_id=body.pdv_id,
        password=body.password,
    )


@router.post(
    "/pdv-authorize",
    response_model=PdvAuthorizeResponse,
    summary="Autorizar override de Supervisor+ no PDV (desconto/cancelamento)",
)
def pdv_authorize(
    body: PdvAuthorizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("sales:write")),
):
    return AuthService(db).pdv_authorize(
        operator=current_user,
        pdv_id=body.pdv_id,
        pin=body.pin,
        actions=body.actions,
    )


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

    data = MeResponse.model_validate(to_user_response(current_user))
    if company:
        data.company = MeCompanyInfo(
            id=company.id,
            legal_name=company.legal_name,
            trade_name=company.trade_name,
            document=company.document,
            has_branches=company.has_branches,
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
    AuthService(db).change_password(
        current_user,
        current_password=body.current_password,
        new_password=body.new_password,
        ip_address=resolve_client_ip(request),
    )
