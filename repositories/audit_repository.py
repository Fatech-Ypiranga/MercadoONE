from datetime import datetime

from sqlmodel import Session, select

from models.audit_log import AuditLog


class AuditRepository:
    @staticmethod
    def create(db: Session, audit_log: AuditLog) -> AuditLog:
        db.add(audit_log)
        db.flush()
        return audit_log

    @staticmethod
    def find_all(
        db: Session,
        *,
        company_id: int | None = None,
        entity_type: str | None = None,
        user_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc())

        if company_id is not None:
            stmt = stmt.where(AuditLog.company_id == company_id)
        if entity_type is not None:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if date_from is not None:
            stmt = stmt.where(AuditLog.created_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(AuditLog.created_at <= date_to)

        stmt = stmt.offset(offset).limit(limit)
        return list(db.exec(stmt).all())
