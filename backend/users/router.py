from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from database.connection import get_db
from shared.identity.dependencies import require_permission
from shared.identity.scope import company_id_of
from shared.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, Page, paginate
from users.models import (
    User,
    UserCreate,
    UserPasswordReset,
    UserPdvPinResponse,
    UserResponse,
    UserUpdate,
)
from users.service import UserService, to_user_response
from utils.enums import UserProfile

router = APIRouter(prefix="/users", tags=["Usuários"])


@router.get("/", response_model=Page[UserResponse], summary="Listar usuários (somente admin)")
def list_users(
    q: str | None = Query(default=None, description="Busca por nome, login, CPF ou PDV ID"),
    profile: UserProfile | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:read")),
):
    company_id = company_id_of(current_user)
    users = UserService(db).list_users(company_id, q=q, profile=profile, is_active=is_active)
    return paginate([to_user_response(user) for user in users], offset=offset, limit=limit)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar usuário (somente admin)",
)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:write")),
):
    company_id = company_id_of(current_user)
    user = UserService(db).create_user(user_in, company_id=company_id, actor_id=current_user.id)
    return to_user_response(user)


@router.get(
    "/{user_id}", response_model=UserResponse, summary="Buscar usuário por ID (somente admin)"
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:read")),
):
    company_id = company_id_of(current_user)
    return to_user_response(UserService(db).get_by_id(user_id, company_id))


@router.put("/{user_id}", response_model=UserResponse, summary="Atualizar usuário (somente admin)")
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:write")),
):
    company_id = company_id_of(current_user)
    user = UserService(db).update_user(
        user_id, user_in, company_id=company_id, actor_id=current_user.id
    )
    return to_user_response(user)


@router.patch(
    "/{user_id}/password",
    response_model=UserResponse,
    summary="Redefinir senha do usuário (somente admin)",
)
def reset_password(
    user_id: int,
    body: UserPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:write")),
):
    company_id = company_id_of(current_user)
    user = UserService(db).reset_password(
        user_id, body.new_password, company_id=company_id, actor_id=current_user.id
    )
    return to_user_response(user)


@router.post(
    "/{user_id}/pdv-pin",
    response_model=UserPdvPinResponse,
    summary="Gerar/regenerar PIN PDV do Supervisor+ (somente admin)",
)
def generate_pdv_pin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:write")),
):
    company_id = company_id_of(current_user)
    return UserService(db).generate_pdv_pin(
        user_id, company_id=company_id, actor_id=current_user.id
    )


@router.post(
    "/{user_id}/pdv-id/regenerate",
    response_model=UserResponse,
    summary="Regenerar ID de PDV (somente admin)",
)
def regenerate_pdv_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:write")),
):
    company_id = company_id_of(current_user)
    user = UserService(db).regenerate_pdv_id(
        user_id, company_id=company_id, actor_id=current_user.id
    )
    return to_user_response(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir usuário (somente admin)",
    description="Remove o usuário permanentemente. Retorna 409 se houver compras vinculadas.",
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:write")),
):
    company_id = company_id_of(current_user)
    UserService(db).delete(user_id, company_id=company_id, actor_id=current_user.id)
