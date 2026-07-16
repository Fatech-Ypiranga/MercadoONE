from sqlalchemy import func, or_
from sqlmodel import Session, select

from models.category import Category
from models.product import Product


class CategoryRepository:
    @staticmethod
    def find_all(
        db: Session,
        company_id: int,
        *,
        q: str | None = None,
        is_active: bool | None = None,
    ) -> list[Category]:
        stmt = select(Category).where(Category.company_id == company_id)
        if q:
            stmt = stmt.where(
                or_(
                    Category.name.ilike(f"%{q}%"),
                    Category.slug.ilike(f"%{q}%"),
                )
            )
        if is_active is not None:
            stmt = stmt.where(Category.is_active.is_(is_active))
        stmt = stmt.order_by(Category.name)
        return list(db.exec(stmt).all())

    @staticmethod
    def find_by_id(db: Session, category_id: int, company_id: int) -> Category | None:
        stmt = select(Category).where(Category.id == category_id, Category.company_id == company_id)
        return db.exec(stmt).first()

    @staticmethod
    def find_by_slug(db: Session, slug: str, company_id: int) -> Category | None:
        stmt = select(Category).where(
            Category.slug == slug, Category.company_id == company_id
        )
        return db.exec(stmt).first()

    @staticmethod
    def create(db: Session, category: Category) -> Category:
        db.add(category)
        db.flush()
        return category

    @staticmethod
    def update(db: Session, category_id: int, company_id: int, **fields) -> Category | None:
        category = CategoryRepository.find_by_id(db, category_id, company_id)
        if not category:
            return None

        for field_name, field_value in fields.items():
            if field_value is not None:
                setattr(category, field_name, field_value)

        db.add(category)
        db.flush()
        return category

    @staticmethod
    def count_products(db: Session, category_id: int, company_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Product)
            .where(Product.category_id == category_id, Product.company_id == company_id)
        )
        return db.exec(stmt).one()

    @staticmethod
    def delete(db: Session, category_id: int, company_id: int) -> bool:
        category = CategoryRepository.find_by_id(db, category_id, company_id)
        if not category:
            return False

        db.delete(category)
        db.flush()
        return True
