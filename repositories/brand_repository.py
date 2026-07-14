from sqlalchemy import func
from sqlmodel import Session, select

from models.product import Brand, Product


class BrandRepository:
    @staticmethod
    def find_all(db: Session, company_id: int) -> list[Brand]:
        stmt = select(Brand).where(Brand.company_id == company_id).order_by(Brand.name)
        return list(db.exec(stmt).all())

    @staticmethod
    def find_by_id(db: Session, brand_id: int, company_id: int) -> Brand | None:
        stmt = select(Brand).where(Brand.id == brand_id, Brand.company_id == company_id)
        return db.exec(stmt).first()

    @staticmethod
    def create(db: Session, brand: Brand) -> Brand:
        db.add(brand)
        db.flush()
        return brand

    @staticmethod
    def update(db: Session, brand_id: int, company_id: int, **fields) -> Brand | None:
        brand = BrandRepository.find_by_id(db, brand_id, company_id)
        if not brand:
            return None

        for field_name, field_value in fields.items():
            if field_value is not None:
                setattr(brand, field_name, field_value)

        db.add(brand)
        db.flush()
        return brand

    @staticmethod
    def count_products(db: Session, brand_id: int, company_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Product)
            .where(Product.brand_id == brand_id, Product.company_id == company_id)
        )
        return db.exec(stmt).one()

    @staticmethod
    def delete(db: Session, brand_id: int, company_id: int) -> bool:
        brand = BrandRepository.find_by_id(db, brand_id, company_id)
        if not brand:
            return False

        db.delete(brand)
        db.flush()
        return True
