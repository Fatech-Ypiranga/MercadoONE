from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

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
