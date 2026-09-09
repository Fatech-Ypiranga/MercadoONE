import re
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from models.product import (
    Product,
    ProductCreate,
    ProductFiscal,
    ProductFiscalCreate,
    ProductMaterialSequence,
    ProductUpdate,
)
from repositories.category_repository import CategoryRepository
from repositories.product_repository import ProductRepository
from repositories.supplier_repository import SupplierRepository
from services.exceptions import (
    BusinessRuleException,
    ConflictException,
    ResourceNotFoundException,
    ValidationError,
)
from shared.audit import AuditService
from utils.enums import AuditAction


class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        product_in: ProductCreate,
        *,
        company_id: int,
        actor_id: int | None = None,
        commit: bool = True,
    ) -> Product:
        try:
            db_product = self._create_uncommitted(
                product_in, company_id=company_id, actor_id=actor_id
            )
            if commit:
                self.db.commit()
                return self.get_by_id(db_product.id, company_id)
            return db_product
        except (ResourceNotFoundException, ValidationError, ConflictException):
            if commit:
                self.db.rollback()
            raise
        except Exception as e:
            if commit:
                self.db.rollback()
            raise BusinessRuleException(f"Error saving product: {e}")

    def _create_uncommitted(
        self,
        product_in: ProductCreate,
        *,
        company_id: int,
        actor_id: int | None = None,
    ) -> Product:
        self._ensure_valid_payload(product_in.name, product_in.sale_price, product_in.category_id)
        self._ensure_category_exists(product_in.category_id, company_id)
        self._ensure_supplier_exists(product_in.primary_supplier_id, company_id)
        self._ensure_unique_sku_barcode(
            sku=product_in.sku,
            barcode=product_in.barcode,
            company_id=company_id,
        )

        if product_in.fiscal:
            self._validate_fiscal(product_in.fiscal)

        product_data = product_in.model_dump(exclude={"fiscal"})
        product_data["company_id"] = company_id
        product_data["material_code"] = self.allocate_material_code(company_id)
        db_product = Product.model_validate(product_data)
        if actor_id is not None:
            db_product.created_by = actor_id
            db_product.updated_by = actor_id
        ProductRepository.create(self.db, db_product)

        if product_in.fiscal:
            db_fiscal = ProductFiscal(product_id=db_product.id, **product_in.fiscal.model_dump())
            self.db.add(db_fiscal)

        if actor_id is not None:
            AuditService(self.db).log(
                user_id=actor_id,
                company_id=company_id,
                action=AuditAction.CREATE,
                entity_type="product",
                entity_id=db_product.id,
            )

        self.db.flush()
        return db_product

    def _ensure_unique_sku_barcode(
        self,
        *,
        sku: str,
        barcode: str | None,
        company_id: int,
        exclude_product_id: int | None = None,
    ) -> None:
        existing_sku = ProductRepository.find_by_sku(self.db, sku, company_id, active_only=False)
        if existing_sku and existing_sku.id != exclude_product_id:
            raise ConflictException(f"Já existe um produto com o SKU '{sku}' nesta empresa.")
        if barcode:
            existing_barcode = ProductRepository.find_by_barcode(
                self.db, barcode, company_id, active_only=False
            )
            if existing_barcode and existing_barcode.id != exclude_product_id:
                raise ConflictException(
                    f"Já existe um produto com o barcode '{barcode}' nesta empresa."
                )

    def list_products(
        self,
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
        return ProductRepository.find_all(
            self.db,
            company_id,
            q=q,
            sku=sku,
            barcode=barcode,
            material_code=material_code,
            category_id=category_id,
            primary_supplier_id=primary_supplier_id,
            is_active=is_active,
        )

    def get_by_sku(self, sku: str, company_id: int) -> Product:
        product = ProductRepository.find_by_sku(self.db, sku, company_id, active_only=False)
        if not product:
            raise ResourceNotFoundException(f"Produto com SKU '{sku}' não encontrado.")
        result = self.get_by_id(product.id, company_id)
        if not result:
            raise ResourceNotFoundException(f"Produto com SKU '{sku}' não encontrado.")
        return result

    def get_by_barcode(self, barcode: str, company_id: int) -> Product:
        if not barcode or not barcode.strip():
            raise ResourceNotFoundException("Barcode inválido ou vazio.")
        product = ProductRepository.find_by_barcode(self.db, barcode, company_id, active_only=False)
        if not product:
            raise ResourceNotFoundException(f"Produto com barcode '{barcode}' não encontrado.")
        result = self.get_by_id(product.id, company_id)
        if not result:
            raise ResourceNotFoundException(f"Produto com barcode '{barcode}' não encontrado.")
        return result

    def get_by_id(self, product_id: int, company_id: int) -> Product | None:
        stmt = (
            select(Product)
            .where(Product.id == product_id, Product.company_id == company_id)
            .options(
                selectinload(Product.category),
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
        if product.primary_supplier_id is None and "primary_supplier_id" not in update_data:
            raise ValidationError(
                "Produtos legados sem fornecedor principal devem informar primary_supplier_id."
            )
        if "primary_supplier_id" in update_data:
            self._ensure_supplier_exists(update_data["primary_supplier_id"], company_id)

        new_sku = update_data.get("sku")
        if new_sku and new_sku != product.sku:
            existing = ProductRepository.find_by_sku(
                self.db, new_sku, company_id, active_only=False
            )
            if existing and existing.id != product_id:
                raise ConflictException(
                    f"Já existe um produto com o SKU '{new_sku}' nesta empresa."
                )

        new_barcode = update_data.get("barcode")
        if new_barcode and new_barcode != product.barcode:
            existing = ProductRepository.find_by_barcode(
                self.db, new_barcode, company_id, active_only=False
            )
            if existing and existing.id != product_id:
                raise ConflictException(
                    f"Já existe um produto com o barcode '{new_barcode}' nesta empresa."
                )

        if product_in.fiscal:
            self._validate_fiscal(product_in.fiscal)

        try:
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
        except (ResourceNotFoundException, ValidationError, ConflictException):
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
        category = CategoryRepository.find_by_id(self.db, category_id, company_id)
        if not category:
            raise ResourceNotFoundException(f"Category with ID {category_id} was not found.")
        if category.parent_id is None:
            children_count = CategoryRepository.count_children(self.db, category_id, company_id)
            if children_count > 0:
                raise ValidationError(
                    "A categoria selecionada possui subcategorias. "
                    "Selecione uma subcategoria (folha) para vincular ao produto."
                )

    def _ensure_supplier_exists(self, supplier_id: int, company_id: int) -> None:
        if not SupplierRepository.find_by_id(self.db, supplier_id, company_id):
            raise ResourceNotFoundException(f"Supplier with ID {supplier_id} was not found.")

    def allocate_material_code(self, company_id: int) -> str:
        if self.db.get_bind().dialect.name == "postgresql":
            self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
                {"key": f"product-material-sequence:{company_id}"},
            )
        counter = self.db.exec(
            select(ProductMaterialSequence)
            .where(ProductMaterialSequence.company_id == company_id)
            .with_for_update()
        ).first()
        if counter is None:
            counter = ProductMaterialSequence(company_id=company_id, last_sequence=1)
        else:
            counter.last_sequence += 1
        if counter.last_sequence > 9_999_999:
            raise ValidationError("Product material code capacity exhausted for this company.")
        self.db.add(counter)
        self.db.flush()
        return f"{counter.last_sequence:07d}"

    def _validate_fiscal(self, fiscal: ProductFiscalCreate) -> None:
        if not re.fullmatch(r"\d{8}", fiscal.ncm):
            raise ValidationError("NCM deve ter exatamente 8 dígitos numéricos.")
        if not re.fullmatch(r"\d{4}", fiscal.cfop_default):
            raise ValidationError("CFOP padrão deve ter exatamente 4 dígitos numéricos.")
        if fiscal.cest is not None and not re.fullmatch(r"\d{7}", fiscal.cest):
            raise ValidationError("CEST deve ter exatamente 7 dígitos numéricos.")
        if not (0 <= fiscal.origem_produto <= 8):
            raise ValidationError("Origem do produto deve ser um valor entre 0 e 8.")
