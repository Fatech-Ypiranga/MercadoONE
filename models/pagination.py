from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 200


class Page(BaseModel, Generic[T]):
    """Listagem paginada: items + total + offset + limit."""

    items: list[T]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=MAX_PAGE_LIMIT)


def paginate(items: list[T], *, offset: int, limit: int) -> Page[T]:
    """Paginação em memória (volumes por tenant ainda modestos)."""
    total = len(items)
    page_items = items[offset : offset + limit]
    return Page(items=page_items, total=total, offset=offset, limit=limit)
