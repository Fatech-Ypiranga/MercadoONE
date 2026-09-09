from typing import Optional

from sqlmodel import SQLModel


class CepResponse(SQLModel):
    zip_code: str
    street: str
    neighborhood: str
    city: str
    state: str
    ibge_code: Optional[str] = None
