from sqlmodel import Session

from models.product import Brand, BrandCreate, BrandUpdate
from repositories.brand_repository import BrandRepository
from services.audit_service import AuditService
from services.exceptions import ConflictException, ResourceNotFoundException
from utils.enums import AuditAction


class BrandService:
    def __init__(self, db: Session):
        self.db = db

    def list_brands(self, company_id: int) -> list[Brand]:
        return BrandRepository.find_all(self.db, company_id)

    def get_by_id(self, brand_id: int, company_id: int) -> Brand:
        brand = BrandRepository.find_by_id(self.db, brand_id, company_id)
        if not brand:
            raise ResourceNotFoundException(f"Brand {brand_id} was not found.")
        return brand

    def create(self, brand_in: BrandCreate, *, company_id: int, actor_id: int) -> Brand:
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
