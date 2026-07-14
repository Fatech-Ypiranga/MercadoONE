from datetime import datetime, timezone

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from models.product import Product, ProductCreate, ProductFiscal, ProductUpdate
from repositories.brand_repository import BrandRepository
from repositories.category_repository import CategoryRepository
from repositories.product_repository import ProductRepository
from services.audit_service import AuditService
from services.exceptions import (
    BusinessRuleException,
    ConflictException,
    ResourceNotFoundException,
    ValidationError,
)
from utils.enums import AuditAction


class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self, product_in: ProductCreate, *, company_id: int, actor_id: int | None = None
    ) -> Product:
        self._ensure_valid_payload(product_in.name, product_in.sale_price, product_in.category_id)
        self._ensure_category_exists(product_in.category_id, company_id)
        if product_in.brand_id:
            self._ensure_brand_exists(product_in.brand_id, company_id)

        try:
            product_data = self._normalize_product_data(product_in.model_dump(exclude={"fiscal"}))
            product_data["company_id"] = company_id
            db_product = Product.model_validate(product_data)
            if actor_id is not None:
                db_product.created_by = actor_id
                db_product.updated_by = actor_id
            ProductRepository.create(self.db, db_product)

            if product_in.fiscal:
                db_fiscal = ProductFiscal(
                    product_id=db_product.id, **product_in.fiscal.model_dump()
                )
                self.db.add(db_fiscal)

            if actor_id is not None:
                AuditService(self.db).log(
                    user_id=actor_id,
                    company_id=company_id,
                    action=AuditAction.CREATE,
                    entity_type="product",
                    entity_id=db_product.id,
                )

            self.db.commit()
            return self.get_by_id(db_product.id, company_id)
        except (ResourceNotFoundException, ValidationError):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessRuleException(f"Error saving product: {e}")

    def get_all(self, company_id: int) -> list[Product]:
        return ProductRepository.find_all(self.db, company_id)

    def get_by_id(self, product_id: int, company_id: int) -> Product | None:
        stmt = (
            select(Product)
            .where(Product.id == product_id, Product.company_id == company_id)
            .options(
                selectinload(Product.category),
                selectinload(Product.brand),
                selectinload(Product.fiscal),
            )
        )
        return self.db.exec(stmt).first()

    def update(
        self,
        product_id: int,
        product_in: ProductUpdate,
        *,
        company_id: int,
        actor_id: int | None = None,
    ) -> Product:
        product = ProductRepository.find_by_id(self.db, product_id, company_id)
        if not product:
            raise ResourceNotFoundException(f"Product with ID {product_id} was not found.")

        update_data = product_in.model_dump(exclude_unset=True, exclude={"fiscal"})
        if "name" in update_data or "sale_price" in update_data or "category_id" in update_data:
            self._ensure_valid_payload(
                update_data.get("name", product.name),
                update_data.get("sale_price", product.sale_price),
                update_data.get("category_id", product.category_id),
            )
        if "category_id" in update_data:
            self._ensure_category_exists(update_data["category_id"], company_id)
        if "brand_id" in update_data and update_data["brand_id"]:
            self._ensure_brand_exists(update_data["brand_id"], company_id)

        try:
            update_data = self._normalize_product_data(update_data)
            for field_name, field_value in update_data.items():
                setattr(product, field_name, field_value)

            product.updated_at = datetime.now(timezone.utc)
            if actor_id is not None:
                product.updated_by = actor_id
            self.db.add(product)
            self.db.flush()

            fiscal_payload = product_in.fiscal
            if fiscal_payload:
                fiscal = self.db.exec(
                    select(ProductFiscal).where(ProductFiscal.product_id == product_id)
                ).first()
                if fiscal:
                    for field_name, field_value in fiscal_payload.model_dump().items():
                        setattr(fiscal, field_name, field_value)
                    self.db.add(fiscal)
                else:
                    self.db.add(ProductFiscal(product_id=product_id, **fiscal_payload.model_dump()))

            if actor_id is not None:
                AuditService(self.db).log(
                    user_id=actor_id,
                    company_id=company_id,
                    action=AuditAction.UPDATE,
                    entity_type="product",
                    entity_id=product_id,
                )

            self.db.commit()
            return self.get_by_id(product_id, company_id)
        except (ResourceNotFoundException, ValidationError):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessRuleException(f"Error updating product: {e}")

    def delete(self, product_id: int, *, company_id: int, actor_id: int | None = None) -> None:
        product = ProductRepository.find_by_id(self.db, product_id, company_id)
        if not product:
            raise ResourceNotFoundException(f"Product with ID {product_id} was not found.")

        if ProductRepository.count_dependencies(self.db, product_id) > 0:
            raise ConflictException(
                "Produto possui movimentos de estoque, vendas ou compras vinculadas."
            )

        deleted = ProductRepository.delete(self.db, product_id, company_id)
        if not deleted:
            raise ResourceNotFoundException(f"Product with ID {product_id} was not found.")

        if actor_id is not None:
            AuditService(self.db).log(
                user_id=actor_id,
                company_id=company_id,
                action=AuditAction.DELETE,
                entity_type="product",
                entity_id=product_id,
            )

        self.db.commit()

    def _ensure_valid_payload(self, name: str, price, category_id: int) -> None:
        if not name or not name.strip():
            raise ValidationError("Product name cannot be empty.")
        if price <= 0:
            raise ValidationError("Product price must be greater than zero.")
        if category_id <= 0:
            raise ValidationError("Category ID must be greater than zero.")

    def _ensure_category_exists(self, category_id: int, company_id: int) -> None:
        if not CategoryRepository.find_by_id(self.db, category_id, company_id):
            raise ResourceNotFoundException(f"Category with ID {category_id} was not found.")

    def _ensure_brand_exists(self, brand_id: int, company_id: int) -> None:
        if not BrandRepository.find_by_id(self.db, brand_id, company_id):
            raise ResourceNotFoundException(f"Brand with ID {brand_id} was not found.")

    def _normalize_product_data(self, data: dict) -> dict:
        # Treat zero as an empty optional brand reference.
        if data.get("brand_id") == 0:
            data["brand_id"] = None
        return data
