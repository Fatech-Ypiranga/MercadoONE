from sqlalchemy import func, or_
from sqlmodel import Session, select

from products.models import Product, ProductFiscal
from purchases.models import PurchaseItem, SupplierProductMapping
from sales.models import SaleItem
from stock.models import StockMovement


class ProductRepository:
    @staticmethod
    def find_by_ids(db: Session, ids: list[int], company_id: int) -> dict[int, Product]:
        """Batch lookup keyed by id, for callers that would otherwise fetch one-by-one."""
        if not ids:
            return {}
        stmt = select(Product).where(Product.id.in_(set(ids)), Product.company_id == company_id)
        return {product.id: product for product in db.exec(stmt).all()}

    @staticmethod
    def find_all(
        db: Session,
        company_id: int,
        *,
        q: str | None = None,
        sku: str | None = None,
        barcode: str | None = None,
        material_code: str | None = None,
        category_id: int | None = None,
        primary_supplier_id: int | None = None,
        is_active: bool | None = None,
    ) -> list[Product]:
        stmt = select(Product).where(Product.company_id == company_id)
        if q:
            stmt = stmt.where(
                or_(
                    Product.name.ilike(f"%{q}%"),
                    Product.sku.ilike(f"%{q}%"),
                    Product.barcode.ilike(f"%{q}%"),
                    Product.material_code.ilike(f"%{q}%"),
                )
            )
        if sku is not None:
            stmt = stmt.where(Product.sku == sku)
        if barcode is not None:
            stmt = stmt.where(Product.barcode == barcode)
        if material_code is not None:
            stmt = stmt.where(Product.material_code == material_code)
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        if primary_supplier_id is not None:
            stmt = stmt.where(Product.primary_supplier_id == primary_supplier_id)
        if is_active is not None:
            stmt = stmt.where(Product.is_active.is_(is_active))
        stmt = stmt.order_by(Product.name)
        return list(db.exec(stmt).all())

    @staticmethod
    def find_by_id(db: Session, product_id: int, company_id: int) -> Product | None:
        stmt = select(Product).where(Product.id == product_id, Product.company_id == company_id)
        return db.exec(stmt).first()

    @staticmethod
    def lock_for_update(db: Session, product_id: int, company_id: int) -> Product | None:
        stmt = (
            select(Product)
            .where(Product.id == product_id, Product.company_id == company_id)
            .with_for_update()
        )
        return db.exec(stmt).first()

    @staticmethod
    def find_by_barcode(
        db: Session, barcode: str, company_id: int, active_only: bool = True
    ) -> Product | None:
        stmt = select(Product).where(
            Product.barcode == barcode,
            Product.company_id == company_id,
        )
        if active_only:
            stmt = stmt.where(Product.is_active.is_(True))
        return db.exec(stmt).first()

    @staticmethod
    def find_by_sku(
        db: Session, sku: str, company_id: int, active_only: bool = True
    ) -> Product | None:
        stmt = select(Product).where(
            Product.sku == sku,
            Product.company_id == company_id,
        )
        if active_only:
            stmt = stmt.where(Product.is_active.is_(True))
        return db.exec(stmt).first()

    @staticmethod
    def create(db: Session, product: Product) -> Product:
        db.add(product)
        db.flush()
        return product

    @staticmethod
    def count_dependencies(db: Session, product_id: int) -> int:
        stock = db.exec(
            select(func.count())
            .select_from(StockMovement)
            .where(StockMovement.product_id == product_id)
        ).one()
        sale_items = db.exec(
            select(func.count()).select_from(SaleItem).where(SaleItem.product_id == product_id)
        ).one()
        purchase_items = db.exec(
            select(func.count())
            .select_from(PurchaseItem)
            .where(PurchaseItem.product_id == product_id)
        ).one()
        return int(stock) + int(sale_items) + int(purchase_items)

    @staticmethod
    def delete(db: Session, product_id: int, company_id: int) -> bool:
        product = ProductRepository.find_by_id(db, product_id, company_id)
        if not product:
            return False

        fiscal = db.exec(
            select(ProductFiscal).where(ProductFiscal.product_id == product_id)
        ).first()
        if fiscal:
            db.delete(fiscal)

        for mapping in db.exec(
            select(SupplierProductMapping).where(SupplierProductMapping.product_id == product_id)
        ).all():
            db.delete(mapping)

        db.delete(product)
        db.flush()
        return True
