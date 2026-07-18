"""Helpers for PDV operator IDs and supervisor PIN credentials."""

from __future__ import annotations

import secrets

from sqlmodel import Session, select

from models.user import User
from utils.enums import UserProfile

PDV_ID_LENGTH = 6
PDV_PIN_LENGTH = 12

PDV_ELIGIBLE_PROFILES = frozenset(
    {
        UserProfile.OPERADOR,
        UserProfile.SUPERVISOR,
        UserProfile.GERENTE,
        UserProfile.ADMIN,
    }
)

SUPERVISOR_PLUS_PROFILES = frozenset(
    {
        UserProfile.SUPERVISOR,
        UserProfile.GERENTE,
        UserProfile.ADMIN,
    }
)


def is_pdv_eligible(profile: UserProfile) -> bool:
    return profile in PDV_ELIGIBLE_PROFILES


def is_supervisor_plus(profile: UserProfile) -> bool:
    return profile in SUPERVISOR_PLUS_PROFILES


def generate_pdv_id(db: Session, company_id: int) -> str:
    """Allocate the next unused 6-digit PDV ID for the company."""
    existing = {
        row
        for row in db.exec(
            select(User.pdv_id).where(User.company_id == company_id, User.pdv_id.is_not(None))
        ).all()
        if row
    }

    for candidate in range(1, 10**PDV_ID_LENGTH):
        code = f"{candidate:0{PDV_ID_LENGTH}d}"
        if code not in existing:
            return code

    raise RuntimeError("No available PDV IDs for this company.")


def generate_pdv_pin() -> str:
    return f"{secrets.randbelow(10**PDV_PIN_LENGTH):0{PDV_PIN_LENGTH}d}"


def ensure_pdv_id(db: Session, user: User) -> None:
    if not is_pdv_eligible(user.profile):
        return
    if user.pdv_id:
        return
    user.pdv_id = generate_pdv_id(db, user.company_id)
