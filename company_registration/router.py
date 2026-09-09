from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from company_registration.models import (
    CompanyRegistrationApprove,
    CompanyRegistrationApproveResponse,
    CompanyRegistrationCreate,
    CompanyRegistrationReject,
    CompanyRegistrationResponse,
)
from company_registration.service import (
    CompanyRegistrationService,
    to_registration_response,
)
from database.connection import get_db
from models.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, Page, paginate
from shared.identity.platform import require_platform_api_key

router = APIRouter(prefix="/company-registrations", tags=["Cadastro de empresas"])


@router.post(
    "/",
    response_model=CompanyRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Solicitar cadastro de empresa (público)",
)
def create_company_registration(
    payload: CompanyRegistrationCreate,
    db: Session = Depends(get_db),
):
    row = CompanyRegistrationService(db).create_request(payload)
    return to_registration_response(row)


@router.get(
    "/",
    response_model=Page[CompanyRegistrationResponse],
    summary="Listar solicitações (gestora / Appsmith)",
)
def list_company_registrations(
    status_filter: str | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    _: str = Depends(require_platform_api_key),
):
    rows = CompanyRegistrationService(db).list_requests(status=status_filter)
    return paginate([to_registration_response(row) for row in rows], offset=offset, limit=limit)


@router.get(
    "/{request_id}",
    response_model=CompanyRegistrationResponse,
    summary="Detalhe da solicitação (gestora / Appsmith)",
)
def get_company_registration(
    request_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_platform_api_key),
):
    row = CompanyRegistrationService(db).get_request(request_id)
    return to_registration_response(row)


@router.post(
    "/{request_id}/approve",
    response_model=CompanyRegistrationApproveResponse,
    summary="Aprovar solicitação e provisionar tenant",
)
def approve_company_registration(
    request_id: int,
    payload: CompanyRegistrationApprove | None = None,
    db: Session = Depends(get_db),
    reviewed_by: str = Depends(require_platform_api_key),
):
    result = CompanyRegistrationService(db).approve(
        request_id,
        payload or CompanyRegistrationApprove(),
        reviewed_by=reviewed_by,
    )
    return result


@router.post(
    "/{request_id}/reject",
    response_model=CompanyRegistrationResponse,
    summary="Rejeitar solicitação",
)
def reject_company_registration(
    request_id: int,
    payload: CompanyRegistrationReject | None = None,
    db: Session = Depends(get_db),
    reviewed_by: str = Depends(require_platform_api_key),
):
    row = CompanyRegistrationService(db).reject(
        request_id,
        payload or CompanyRegistrationReject(),
        reviewed_by=reviewed_by,
    )
    return to_registration_response(row)
