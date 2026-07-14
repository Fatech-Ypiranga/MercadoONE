from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session

from models.audit_log import AuditLog
from repositories.audit_repository import AuditRepository
from utils.enums import AuditAction


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        *,
        user_id: int | None,
        action: AuditAction,
        entity_type: str,
        entity_id: int,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        company_id: int | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            company_id=company_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
            created_at=datetime.now(timezone.utc),
        )
        return AuditRepository.create(self.db, entry)

    def list_logs(
        self,
        *,
        company_id: int | None = None,
        entity_type: str | None = None,
        user_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[AuditLog]:
        return AuditRepository.find_all(
            self.db,
            company_id=company_id,
            entity_type=entity_type,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            offset=offset,
            limit=limit,
        )
