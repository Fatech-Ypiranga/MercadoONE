"""Password reset by email: request, check and confirm a single-use token."""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlmodel import Session, select

from auth.models import PasswordResetToken
from organization.repository import CompanyRepository
from shared import mailer
from shared.audit import AuditService
from shared.exceptions import ValidationError
from shared.identity.security import hash_password
from users.models import User
from utils.cnpj import normalize_cnpj
from utils.enums import AuditAction

logger = logging.getLogger(__name__)

RESEND_COOLDOWN_SECONDS = 60
INVALID_TOKEN_MESSAGE = "Invalid or expired reset link."


def _ttl_minutes() -> int:
    return int(os.getenv("PASSWORD_RESET_TTL_MINUTES", "30"))


def _frontend_base_url() -> str:
    return os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def build_reset_link(token: str) -> str:
    return f"{_frontend_base_url()}/nova-senha?token={token}"


def deliver_reset_email(email: str, token: str) -> None:
    """Send the reset email; failures are logged, never raised (no account enumeration)."""
    link = build_reset_link(token)
    body = (
        "Recebemos um pedido para redefinir a senha da sua conta no MercadoONE.\n\n"
        f"Use o link abaixo (válido por {_ttl_minutes()} minutos, uso único):\n{link}\n\n"
        "Se você não pediu, ignore esta mensagem; sua senha continua a mesma."
    )
    try:
        mailer.send_email(email, "Redefinição de senha - MercadoONE", body)
    except Exception:
        logger.exception("Failed to send password reset email")


class PasswordResetService:
    def __init__(self, db: Session):
        self.db = db

    def request_reset(self, *, email: str, company_document: str) -> tuple[str, str] | None:
        """Create a token for an active user with this email. Returns (email, raw_token) or None.

        Callers must answer identically whether or not a user was found.
        """
        document = normalize_cnpj(company_document)
        company = CompanyRepository.find_by_document(self.db, document) if document else None
        if not company or not company.is_active:
            return None

        normalized = email.strip().lower()
        user = self.db.exec(
            select(User).where(User.company_id == company.id, func.lower(User.email) == normalized)
        ).first()
        if not user or not user.is_active or not user.email:
            return None

        now = datetime.now(timezone.utc)
        pending = list(
            self.db.exec(
                select(PasswordResetToken).where(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.used_at.is_(None),  # type: ignore[union-attr]
                )
            ).all()
        )
        if any(
            (now - token.created_at).total_seconds() < RESEND_COOLDOWN_SECONDS for token in pending
        ):
            return None
        for token in pending:
            token.used_at = now  # invalidate older links
            self.db.add(token)

        raw = secrets.token_urlsafe(32)
        self.db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw),
                expires_at=now + timedelta(minutes=_ttl_minutes()),
            )
        )
        self.db.commit()
        return user.email, raw

    def _find_valid(self, token: str) -> PasswordResetToken | None:
        record = self.db.exec(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(token))
        ).first()
        if not record or record.used_at is not None:
            return None
        if record.expires_at <= datetime.now(timezone.utc):
            return None
        return record

    def check(self, token: str) -> bool:
        return self._find_valid(token) is not None

    def confirm(self, *, token: str, new_password: str, ip_address: str | None = None) -> None:
        # Local import: auth.service imports this module's siblings at import time.
        from auth.service import bump_token_version

        record = self._find_valid(token)
        user = self.db.get(User, record.user_id) if record else None
        if not record or not user or not user.is_active:
            raise ValidationError(INVALID_TOKEN_MESSAGE)

        now = datetime.now(timezone.utc)
        user.password_hash = hash_password(new_password)
        bump_token_version(user)  # signs the user out everywhere
        user.updated_at = now
        user.updated_by = user.id
        record.used_at = now
        self.db.add(user)
        self.db.add(record)
        AuditService(self.db).log(
            user_id=user.id,
            company_id=user.company_id,
            action=AuditAction.PASSWORD_CHANGE,
            entity_type="user",
            entity_id=user.id,
            details={"via": "password_reset"},
            ip_address=ip_address,
        )
        self.db.commit()
