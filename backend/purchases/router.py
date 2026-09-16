from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlmodel import Session

from database.connection import get_db
from purchases.models import (
    NfeUploadPreviewResponse,
    PurchaseConfirmRequest,
    PurchaseOrderDetailResponse,
    PurchaseOrderResponse,
)
from purchases.service import PurchaseService
from shared.exceptions import ValidationError
from shared.identity.dependencies import require_permission
from shared.identity.scope import company_id_of, resolve_store_id
from shared.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, Page
from users.models import User
from utils.enums import PurchaseStatus

router = APIRouter(prefix="/purchases", tags=["Compras"])

# A real NF-e XML is a few hundred KB at most; this caps memory use and
# in-request processing time against an oversized/malicious upload
# (docs/ROADMAP.md SEC-01/NFE-01).
MAX_XML_UPLOAD_BYTES = 5 * 1024 * 1024


@router.post(
    "/upload-xml",
    response_model=NfeUploadPreviewResponse,
    summary="Enviar XML de NF-e e pré-visualizar importação de compra",
)
async def upload_purchase_xml(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("purchases:write")),
):
    company_id = company_id_of(current_user)
    if file.filename and not file.filename.lower().endswith(".xml"):
        raise ValidationError("Only .xml files are accepted for NF-e import.")

    content = await file.read(MAX_XML_UPLOAD_BYTES + 1)
    if len(content) > MAX_XML_UPLOAD_BYTES:
        raise ValidationError(
            f"XML file exceeds the maximum upload size of {MAX_XML_UPLOAD_BYTES} bytes."
        )
    return PurchaseService(db).preview_xml_upload(content, company_id=company_id)


@router.post(
    "/confirm",
    response_model=PurchaseOrderDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirmar importação de compra revisada",
)
def confirm_purchase(
    payload: PurchaseConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("purchases:write")),
):
    company_id = company_id_of(current_user)
    store_id = resolve_store_id(db, current_user, payload.store_id)
    return PurchaseService(db).confirm_purchase(
        payload, actor_id=current_user.id, company_id=company_id, store_id=store_id
    )


@router.get("/", response_model=Page[PurchaseOrderResponse], summary="Listar compras")
def list_purchases(
    supplier_id: Annotated[int | None, Query()] = None,
    status_filter: Annotated[PurchaseStatus | None, Query(alias="status")] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    store_id: Annotated[int | None, Query()] = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("purchases:read")),
):
    company_id = company_id_of(current_user)
    purchases, total = PurchaseService(db).list_purchases(
        company_id,
        supplier_id=supplier_id,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        store_id=store_id,
        offset=offset,
        limit=limit,
    )
    return Page(items=purchases, total=total, offset=offset, limit=limit)


@router.get(
    "/{purchase_id}", response_model=PurchaseOrderDetailResponse, summary="Buscar compra por ID"
)
def get_purchase(
    purchase_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("purchases:read")),
):
    company_id = company_id_of(current_user)
    return PurchaseService(db).get_purchase_detail(purchase_id, company_id)


@router.post(
    "/{purchase_id}/cancel",
    response_model=PurchaseOrderDetailResponse,
    summary="Cancelar compra confirmada e estornar estoque",
)
def cancel_purchase(
    purchase_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("purchases:write")),
):
    company_id = company_id_of(current_user)
    return PurchaseService(db).cancel_purchase(
        purchase_id, company_id=company_id, actor_id=current_user.id
    )
