from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from models.category import Category, CategoryCreate, CategoryUpdate
from repositories.category_repository import CategoryRepository
from services.audit_service import AuditService
from services.exceptions import ConflictException, ResourceNotFoundException
from utils.enums import AuditAction


class CategoryService:
    def __init__(self, db: Session):
        self.db = db

    def list_categories(self, company_id: int) -> list[Category]:
        return CategoryRepository.find_all(self.db, company_id)

    def get_by_id(self, category_id: int, company_id: int) -> Category:
        stmt = (
            select(Category)
            .where(Category.id == category_id, Category.company_id == company_id)
            .options(selectinload(Category.products))
        )
        category = self.db.exec(stmt).first()
        if not category:
            raise ResourceNotFoundException(f"Category {category_id} was not found.")
        return category

    def create(self, category_in: CategoryCreate, *, company_id: int, actor_id: int) -> Category:
        category = Category.model_validate({**category_in.model_dump(), "company_id": company_id})
        category.created_by = actor_id
        category.updated_by = actor_id
        CategoryRepository.create(self.db, category)

        AuditService(self.db).log(
            user_id=actor_id,
            company_id=company_id,
            action=AuditAction.CREATE,
            entity_type="category",
            entity_id=category.id,
        )
        self.db.commit()
        self.db.refresh(category)
        return category

    def update(
        self,
        category_id: int,
        category_in: CategoryUpdate,
        *,
        company_id: int,
        actor_id: int,
    ) -> Category:
        category = CategoryRepository.update(
            self.db,
            category_id,
            company_id,
            **category_in.model_dump(exclude_unset=True),
        )
        if not category:
            raise ResourceNotFoundException(f"Category {category_id} was not found.")

        category.updated_by = actor_id
        AuditService(self.db).log(
            user_id=actor_id,
            company_id=company_id,
            action=AuditAction.UPDATE,
            entity_type="category",
            entity_id=category_id,
        )
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete(self, category_id: int, *, company_id: int, actor_id: int) -> None:
        if CategoryRepository.count_products(self.db, category_id, company_id) > 0:
            raise ConflictException("Categoria possui produtos vinculados.")

        deleted = CategoryRepository.delete(self.db, category_id, company_id)
        if not deleted:
            raise ResourceNotFoundException(f"Category {category_id} was not found.")

        AuditService(self.db).log(
            user_id=actor_id,
            company_id=company_id,
            action=AuditAction.DELETE,
            entity_type="category",
            entity_id=category_id,
        )
        self.db.commit()
