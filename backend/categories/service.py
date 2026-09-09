from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from categories.models import Category, CategoryCreate, CategoryUpdate
from categories.repository import _UNSET, CategoryRepository
from shared.audit import AuditService
from shared.exceptions import ConflictException, ResourceNotFoundException, ValidationError
from utils.enums import AuditAction


class CategoryService:
    def __init__(self, db: Session):
        self.db = db

    def list_categories(
        self,
        company_id: int,
        *,
        q: str | None = None,
        is_active: bool | None = None,
        parent_id=_UNSET,
    ) -> list[Category]:
        return CategoryRepository.find_all(
            self.db, company_id, q=q, is_active=is_active, parent_id=parent_id
        )

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

    def get_by_slug(self, slug: str, company_id: int) -> Category:
        category = CategoryRepository.find_by_slug(self.db, slug, company_id)
        if not category:
            raise ResourceNotFoundException(f"Category with slug '{slug}' was not found.")
        return category

    def _validate_parent(self, parent_id: int, company_id: int) -> Category:
        parent = CategoryRepository.find_by_id(self.db, parent_id, company_id)
        if not parent:
            raise ResourceNotFoundException(
                f"Categoria pai {parent_id} não encontrada nesta empresa."
            )
        if parent.parent_id is not None:
            raise ValidationError(
                "Não é permitido criar subcategoria de uma subcategoria (máximo 1 nível)."
            )
        return parent

    def create(self, category_in: CategoryCreate, *, company_id: int, actor_id: int) -> Category:
        if CategoryRepository.find_by_slug(self.db, category_in.slug, company_id):
            raise ConflictException(
                f"Já existe uma categoria com o slug '{category_in.slug}' nesta empresa."
            )

        if category_in.parent_id is not None:
            self._validate_parent(category_in.parent_id, company_id)

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
        update_data = category_in.model_dump(exclude_unset=True)

        if "slug" in update_data and update_data["slug"] is not None:
            existing = CategoryRepository.find_by_slug(self.db, update_data["slug"], company_id)
            if existing and existing.id != category_id:
                raise ConflictException(
                    f"Já existe uma categoria com o slug '{update_data['slug']}' nesta empresa."
                )

        if "parent_id" in update_data:
            new_parent_id = update_data["parent_id"]
            if new_parent_id is not None:
                if new_parent_id == category_id:
                    raise ValidationError("Uma categoria não pode ser pai de si mesma.")
                self._validate_parent(new_parent_id, company_id)
                if CategoryRepository.count_children(self.db, category_id, company_id) > 0:
                    raise ValidationError(
                        "Não é possível definir um pai para uma categoria que já possui subcategorias."
                    )

        category = CategoryRepository.update(
            self.db,
            category_id,
            company_id,
            **update_data,
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

        if CategoryRepository.count_children(self.db, category_id, company_id) > 0:
            raise ConflictException(
                "Categoria possui subcategorias vinculadas. Remova as subcategorias antes."
            )

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
