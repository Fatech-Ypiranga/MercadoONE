from sqlmodel import Session

from models.user import User
from repositories.store_repository import StoreRepository
from services.exceptions import ForbiddenException, ValidationError


def company_id_of(user: User) -> int:
    if user.company_id is None:
        raise ForbiddenException("User is not linked to a company.")
    return user.company_id


def resolve_store_id(
    db: Session,
    user: User,
    store_id: int | None = None,
) -> int:
    """Resolve store from request or user default; must belong to user's company."""
    resolved = store_id if store_id is not None else user.default_store_id
    if resolved is None:
        raise ValidationError("store_id is required (or set a default store on the user).")

    store = StoreRepository.find_by_id_for_company(db, resolved, company_id_of(user))
    if not store or not store.is_active:
        raise ValidationError("Invalid or inactive store for this company.")
    return store.id


