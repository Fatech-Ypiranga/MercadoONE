from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from models.sale import Sale, SaleStatus
from models.stock_movement import MovementReason, MovementType, StockMovement
from repositories.customer_repository import CustomerRepository
from repositories.movement_repository import MovementRepository
from repositories.product_repository import ProductRepository
from repositories.sale_repository import SaleRepository
from repositories.stock_repository import StockRepository
from services.audit_service import AuditService
from services.exceptions import (
    BusinessRuleException,
    InsufficientStockException,
    ResourceNotFoundException,
    ValidationError,
)
from utils.enums import AuditAction


class SaleService:
    def __init__(self, db: Session):
        self.db = db

    def process_sale(
        self,
        customer_id: int | None,
        items: list[dict],
        user_id: int,
        *,
        company_id: int,
        store_id: int,
        payment_method: str | None = None,
    ) -> Sale:
        if not items:
            raise ValidationError("A sale needs at least one item.")

        if customer_id is not None and not CustomerRepository.find_by_id(
            self.db, customer_id, company_id
        ):
            raise ResourceNotFoundException(f"Customer with ID {customer_id} was not found.")

        for item in items:
            if item["quantity"] <= 0:
                raise ValidationError("Each item quantity must be greater than zero.")

        try:
            validated_items: list[dict] = []
            total_sale_price = Decimal("0.00")

            for item in items:
                product_id = item["product_id"]
                quantity = item["quantity"]

                product = ProductRepository.lock_for_update(self.db, product_id, company_id)
                if not product:
                    raise ResourceNotFoundException(f"Product with ID {product_id} was not found.")
                if not product.is_active:
                    raise ValidationError(f"Product '{product.name}' is inactive.")

                current_stock = StockRepository.get_current_stock(self.db, product_id, store_id)
                if current_stock < quantity:
                    raise InsufficientStockException(
                        f"Not enough stock for '{product.name}'. Available: {current_stock}, requested: {quantity}."
                    )

                item_total = Decimal(product.sale_price) * Decimal(quantity)
                total_sale_price += item_total

                validated_items.append(
                    {
                        "product": product,
                        "quantity": quantity,
                        "unit_price": product.sale_price,
                    }
                )

            sale = SaleRepository.create(
                self.db,
                company_id=company_id,
                store_id=store_id,
                customer_id=customer_id,
                user_id=user_id,
                total_amount=total_sale_price,
                payment_method=payment_method,
                status=SaleStatus.CONCLUIDA,
                created_by=user_id,
            )

            for validated_item in validated_items:
                SaleRepository.add_item(
                    self.db,
                    sale_id=sale.id,
                    product_id=validated_item["product"].id,
                    quantity=validated_item["quantity"],
                    unit_price=validated_item["unit_price"],
                )

                MovementRepository.register_movement(
                    self.db,
                    StockMovement(
                        company_id=company_id,
                        store_id=store_id,
                        product_id=validated_item["product"].id,
                        quantity=validated_item["quantity"],
                        type=MovementType.SAIDA,
                        reason=MovementReason.VENDA,
                        source_sale_id=sale.id,
                    ),
                )

            AuditService(self.db).log(
                user_id=user_id,
                company_id=company_id,
                action=AuditAction.CREATE,
                entity_type="sale",
                entity_id=sale.id,
            )

            self.db.commit()
            return self.get_by_id(sale.id, company_id)
        except (ValidationError, ResourceNotFoundException, InsufficientStockException):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessRuleException(f"Sale processing failed. Transaction cancelled: {e}")

    def cancel_sale(self, sale_id: int, *, company_id: int, actor_id: int) -> Sale:
        sale = SaleRepository.find_by_id(self.db, sale_id, company_id)
        if not sale:
            raise ResourceNotFoundException(f"Sale with ID {sale_id} was not found.")

        if sale.status == SaleStatus.CANCELADA:
            raise ValidationError("Sale is already cancelled.")
        if sale.status == SaleStatus.SUSPENSA:
            raise ValidationError("Suspended sales cannot be cancelled via this endpoint.")

        sale_items = SaleRepository.find_items_by_sale(self.db, sale_id)

        try:
            for item in sale_items:
                product = ProductRepository.lock_for_update(self.db, item.product_id, company_id)
                if not product:
                    raise ResourceNotFoundException(
                        f"Product with ID {item.product_id} was not found."
                    )
                MovementRepository.register_movement(
                    self.db,
                    StockMovement(
                        company_id=sale.company_id,
                        store_id=sale.store_id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        type=MovementType.ENTRADA,
                        reason=MovementReason.DEVOLUCAO,
                        source_sale_id=sale.id,
                    ),
                )

            SaleRepository.update_status(
                self.db, sale_id, company_id, SaleStatus.CANCELADA, updated_by=actor_id
            )
            AuditService(self.db).log(
                user_id=actor_id,
                company_id=company_id,
                action=AuditAction.UPDATE,
                entity_type="sale",
                entity_id=sale_id,
                details={"status": SaleStatus.CANCELADA},
            )
            self.db.commit()
            return self.get_by_id(sale_id, company_id)
        except (ValidationError, ResourceNotFoundException):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessRuleException(f"Sale cancellation failed: {e}")

    def get_by_id(self, sale_id: int, company_id: int) -> Sale | None:
        stmt = (
            select(Sale)
            .where(Sale.id == sale_id, Sale.company_id == company_id)
            .options(selectinload(Sale.items))
        )
        return self.db.exec(stmt).first()

    def list_sales(
        self,
        company_id: int,
        *,
        customer_id: int | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        store_id: int | None = None,
    ) -> list[Sale]:
        stmt = (
            select(Sale)
            .where(Sale.company_id == company_id)
            .order_by(Sale.sale_date.desc())
            .options(selectinload(Sale.items))
        )

        if customer_id is not None:
            stmt = stmt.where(Sale.customer_id == customer_id)
        if status is not None:
            stmt = stmt.where(Sale.status == status)
        if date_from is not None:
            stmt = stmt.where(Sale.sale_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Sale.sale_date <= date_to)
        if store_id is not None:
            stmt = stmt.where(Sale.store_id == store_id)

        return list(self.db.exec(stmt).all())
