"""Helpers for PDV operator IDs and supervisor PIN credentials."""

from __future__ import annotations

import secrets

from sqlmodel import Session, select

from models.user import User
from utils.enums import UserProfile

PDV_ID_LENGTH = 6
PDV_PIN_LENGTH = 12
PDV_ID_MAX_ATTEMPTS = 64

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

# Predictable codes that operators should not receive as PDV IDs.
_WEAK_PDV_IDS = frozenset(
    {
        "000000",
        "111111",
        "222222",
        "333333",
        "444444",
        "555555",
        "666666",
        "777777",
        "888888",
        "999999",
        "123456",
        "654321",
        "012345",
        "543210",
        "112233",
        "121212",
    }
)


def is_pdv_eligible(profile: UserProfile) -> bool:
    return profile in PDV_ELIGIBLE_PROFILES


def is_supervisor_plus(profile: UserProfile) -> bool:
    return profile in SUPERVISOR_PLUS_PROFILES


def is_weak_pdv_id(code: str) -> bool:
    return code in _WEAK_PDV_IDS


def generate_pdv_id(db: Session, company_id: int) -> str:
    """Allocate a random unused 6-digit PDV ID for the company."""
    existing = {
        row
        for row in db.exec(
            select(User.pdv_id).where(User.company_id == company_id, User.pdv_id.is_not(None))
        ).all()
        if row
    }

    for _ in range(PDV_ID_MAX_ATTEMPTS):
        code = f"{secrets.randbelow(10**PDV_ID_LENGTH):0{PDV_ID_LENGTH}d}"
        if code in existing or is_weak_pdv_id(code):
            continue
        return code

    raise RuntimeError("Unable to allocate a unique PDV ID for this company.")


def generate_pdv_pin() -> str:
    return f"{secrets.randbelow(10**PDV_PIN_LENGTH):0{PDV_PIN_LENGTH}d}"


def ensure_pdv_id(db: Session, user: User) -> None:
    if not is_pdv_eligible(user.profile):
        return
    if user.pdv_id:
        return
    user.pdv_id = generate_pdv_id(db, user.company_id)
