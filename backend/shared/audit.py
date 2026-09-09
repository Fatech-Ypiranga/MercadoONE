"""Audit trail: cross-cutting infrastructure written to by nearly every slice.

Not a business feature on its own — kept in `shared` because every write-side
service (users, products, sales, purchases, ...) needs to log to it, and
forcing that dependency through a "slice" would make every other slice depend
on one arbitrarily chosen slice.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Session, SQLModel, select

from utils.enums import AuditAction, enum_column


class AuditLogBase(SQLModel):
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    company_id: Optional[int] = Field(default=None, foreign_key="companies.id", index=True)
    action: AuditAction
    entity_type: str = Field(max_length=50, index=True)
    entity_id: int
    details: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    ip_address: Optional[str] = Field(default=None, max_length=45)


class AuditLogResponse(AuditLogBase):
    id: int
    created_at: datetime


class AuditLog(AuditLogBase, table=True):
    __tablename__ = "audit_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    action: AuditAction = Field(sa_column=enum_column(AuditAction))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )


class AuditRepository:
    @staticmethod
    def create(db: Session, audit_log: AuditLog) -> AuditLog:
        db.add(audit_log)
        db.flush()
        return audit_log

    @staticmethod
    def _filtered_stmt(
        *,
        company_id: int | None = None,
        entity_type: str | None = None,
        user_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ):
        stmt = select(AuditLog)
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
        return stmt

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
        stmt = (
            AuditRepository._filtered_stmt(
                company_id=company_id,
                entity_type=entity_type,
                user_id=user_id,
                date_from=date_from,
                date_to=date_to,
            )
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(db.exec(stmt).all())

    @staticmethod
    def count_all(
        db: Session,
        *,
        company_id: int | None = None,
        entity_type: str | None = None,
        user_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        filtered = AuditRepository._filtered_stmt(
            company_id=company_id,
            entity_type=entity_type,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        ).subquery()
        return int(db.exec(select(func.count()).select_from(filtered)).one() or 0)


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

    def count_logs(
        self,
        *,
        company_id: int | None = None,
        entity_type: str | None = None,
        user_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        return AuditRepository.count_all(
            self.db,
            company_id=company_id,
            entity_type=entity_type,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )
