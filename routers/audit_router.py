from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from auth.dependencies import require_permission
from auth.scope import company_id_of
from database.connection import get_db
from models.audit_log import AuditLogResponse
from models.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, Page
from models.user import User
from services.audit_service import AuditService

router = APIRouter(prefix="/audit-log", tags=["Auditoria"])


@router.get(
    "/",
    response_model=Page[AuditLogResponse],
    summary="Listar entradas de auditoria (somente admin)",
)
def list_audit_log(
    entity_type: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("audit:read")),
):
    company_id = company_id_of(current_user)
    logs = AuditService(db).list_logs(
        company_id=company_id,
        entity_type=entity_type,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )
    # total via a parallel unpaginated count path (same filters)
    all_matching = AuditService(db).list_logs(
        company_id=company_id,
        entity_type=entity_type,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        offset=0,
        limit=10_000,
    )
    return Page(items=logs, total=len(all_matching), offset=offset, limit=limit)
