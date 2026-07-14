from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from auth.dependencies import require_permission
from auth.scope import company_id_of
from database.connection import get_db
from models.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, Page, paginate
from models.user import User, UserCreate, UserPasswordReset, UserResponse, UserUpdate
from services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Usuários"])


@router.get("/", response_model=Page[UserResponse], summary="Listar usuários (somente admin)")
def list_users(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:read")),
):
    company_id = company_id_of(current_user)
    return paginate(UserService(db).list_users(company_id), offset=offset, limit=limit)


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
    return UserService(db).create_user(user_in, company_id=company_id, actor_id=current_user.id)


@router.get(
    "/{user_id}", response_model=UserResponse, summary="Buscar usuário por ID (somente admin)"
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:read")),
):
    company_id = company_id_of(current_user)
    return UserService(db).get_by_id(user_id, company_id)


@router.put("/{user_id}", response_model=UserResponse, summary="Atualizar usuário (somente admin)")
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:write")),
):
    company_id = company_id_of(current_user)
    return UserService(db).update_user(
        user_id, user_in, company_id=company_id, actor_id=current_user.id
    )


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
    return UserService(db).reset_password(
        user_id, body.new_password, company_id=company_id, actor_id=current_user.id
    )


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
