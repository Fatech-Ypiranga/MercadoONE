from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from auth.password_reset import PasswordResetService, deliver_reset_email
from auth.service import AuthService
from database.connection import get_db
from middleware.security import resolve_client_ip
from shared.identity.dependencies import get_current_user, require_permission
from users.models import MeResponse, User

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


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=150)
    company_document: str = Field(description="CNPJ da empresa (com ou sem pontuação)")


class PasswordResetRequestResponse(BaseModel):
    message: str


class PasswordResetTokenRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class PasswordResetCheckResponse(BaseModel):
    valid: bool


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: str = Field(min_length=6, max_length=128)


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
    return AuthService(db).build_me_response(current_user)


@router.post(
    "/password/request",
    response_model=PasswordResetRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Pedir redefinição de senha por e-mail",
)
def request_password_reset(
    body: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Same answer whether or not the account exists (no user enumeration).
    result = PasswordResetService(db).request_reset(
        email=body.email, company_document=body.company_document
    )
    if result:
        email, token = result
        background_tasks.add_task(deliver_reset_email, email, token)
    return PasswordResetRequestResponse(
        message="Se existir uma conta com esse e-mail, enviamos o link de redefinição."
    )


@router.post(
    "/password/check",
    response_model=PasswordResetCheckResponse,
    summary="Verificar se o link de redefinição ainda é válido",
)
def check_password_reset(body: PasswordResetTokenRequest, db: Session = Depends(get_db)):
    return PasswordResetCheckResponse(valid=PasswordResetService(db).check(body.token))


@router.post(
    "/password/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Definir nova senha com o link de redefinição",
)
def confirm_password_reset(
    body: PasswordResetConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    PasswordResetService(db).confirm(
        token=body.token,
        new_password=body.new_password,
        ip_address=resolve_client_ip(request),
    )


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
