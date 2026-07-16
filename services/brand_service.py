from sqlmodel import Session

from models.product import Brand, BrandCreate, BrandUpdate
from repositories.brand_repository import BrandRepository
from services.audit_service import AuditService
from services.exceptions import ConflictException, ResourceNotFoundException
from utils.enums import AuditAction


class BrandService:
    def __init__(self, db: Session):
        self.db = db

    def list_brands(self, company_id: int, *, q: str | None = None) -> list[Brand]:
        return BrandRepository.find_all(self.db, company_id, q=q)

    def get_by_id(self, brand_id: int, company_id: int) -> Brand:
        brand = BrandRepository.find_by_id(self.db, brand_id, company_id)
        if not brand:
            raise ResourceNotFoundException(f"Brand {brand_id} was not found.")
        return brand

    def get_by_name(self, name: str, company_id: int) -> Brand:
        brand = BrandRepository.find_by_name(self.db, name.strip(), company_id)
        if not brand:
            raise ResourceNotFoundException(f"Brand '{name}' was not found.")
        return brand

    def _check_duplicate_name(
        self, name: str, company_id: int, exclude_id: int | None = None
    ) -> None:
        if exclude_id is not None:
            existing = BrandRepository.find_by_name_excluding(
                self.db, name, company_id, exclude_id
            )
        else:
            existing = BrandRepository.find_by_name(self.db, name, company_id)
        if existing:
            raise ConflictException(
                f"Já existe uma marca com o nome '{name.strip()}' nesta empresa."
            )

    def create(self, brand_in: BrandCreate, *, company_id: int, actor_id: int) -> Brand:
        self._check_duplicate_name(brand_in.name, company_id)

        brand = Brand.model_validate({**brand_in.model_dump(), "company_id": company_id})
        brand.created_by = actor_id
        brand.updated_by = actor_id
        BrandRepository.create(self.db, brand)

        AuditService(self.db).log(
            user_id=actor_id,
            company_id=company_id,
            action=AuditAction.CREATE,
            entity_type="brand",
            entity_id=brand.id,
        )
        self.db.commit()
        self.db.refresh(brand)
        return brand

    def update(
        self, brand_id: int, brand_in: BrandUpdate, *, company_id: int, actor_id: int
    ) -> Brand:
        if brand_in.name is not None:
            self._check_duplicate_name(brand_in.name, company_id, exclude_id=brand_id)

        brand = BrandRepository.update(
            self.db, brand_id, company_id, **brand_in.model_dump(exclude_unset=True)
        )
        if not brand:
            raise ResourceNotFoundException(f"Brand {brand_id} was not found.")

        brand.updated_by = actor_id
        AuditService(self.db).log(
            user_id=actor_id,
            company_id=company_id,
            action=AuditAction.UPDATE,
            entity_type="brand",
            entity_id=brand_id,
        )
        self.db.commit()
        self.db.refresh(brand)
        return brand

    def delete(self, brand_id: int, *, company_id: int, actor_id: int) -> None:
        if BrandRepository.count_products(self.db, brand_id, company_id) > 0:
            raise ConflictException("Marca possui produtos vinculados.")

        deleted = BrandRepository.delete(self.db, brand_id, company_id)
        if not deleted:
            raise ResourceNotFoundException(f"Brand {brand_id} was not found.")

        AuditService(self.db).log(
            user_id=actor_id,
            company_id=company_id,
            action=AuditAction.DELETE,
            entity_type="brand",
            entity_id=brand_id,
        )
        self.db.commit()
