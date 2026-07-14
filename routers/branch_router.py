from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from auth.dependencies import require_permission
from auth.scope import company_id_of
from database.connection import get_db
from models.company import BranchCreate, BranchResponse, BranchUpdate
from models.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, Page, paginate
from models.user import User
from services.org_service import OrgService

router = APIRouter(prefix="/branches", tags=["Filiais"])


@router.get("/", response_model=Page[BranchResponse], summary="Listar filiais")
def list_branches(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("branches:read")),
):
    company_id = company_id_of(current_user)
    return paginate(OrgService(db).list_branches(company_id), offset=offset, limit=limit)


@router.get("/{branch_id}", response_model=BranchResponse, summary="Buscar filial por ID")
def get_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("branches:read")),
):
    company_id = company_id_of(current_user)
    return OrgService(db).get_branch(branch_id, company_id)


@router.post(
    "/",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar filial",
)
def create_branch(
    branch_in: BranchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("branches:write")),
):
    company_id = company_id_of(current_user)
    return OrgService(db).create_branch(branch_in, company_id=company_id)


@router.put("/{branch_id}", response_model=BranchResponse, summary="Atualizar filial")
def update_branch(
    branch_id: int,
    branch_in: BranchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("branches:write")),
):
    company_id = company_id_of(current_user)
    return OrgService(db).update_branch(branch_id, branch_in, company_id=company_id)


@router.delete(
    "/{branch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir filial",
)
def delete_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("branches:write")),
):
    company_id = company_id_of(current_user)
    OrgService(db).delete_branch(branch_id, company_id=company_id)
