from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from auth.permissions import has_permission
from models.sale import Sale, SaleStatus
from models.stock_movement import MovementReason, MovementType, StockMovement
from models.user import User
from repositories.customer_repository import CustomerRepository
from repositories.movement_repository import MovementRepository
from repositories.product_repository import ProductRepository
from repositories.sale_repository import SaleRepository
from repositories.stock_repository import StockRepository
from repositories.user_repository import UserRepository
from services.audit_service import AuditService
from services.auth_service import AuthService
from services.exceptions import (
    BusinessRuleException,
    InsufficientStockException,
    ResourceNotFoundException,
    UnauthorizedException,
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
        discount_amount: Decimal | None = None,
        supervisor_authorization: str | None = None,
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

        discount = Decimal(discount_amount or 0)
        if discount < 0:
            raise ValidationError("Discount amount cannot be negative.")

        actor = UserRepository.find_by_id(self.db, user_id, company_id=company_id)
        if not actor:
            raise ResourceNotFoundException(f"User with ID {user_id} was not found.")

        if discount > 0:
            self._ensure_discount_authorized(
                actor=actor,
                supervisor_authorization=supervisor_authorization,
            )

        try:
            validated_items: list[dict] = []
            total_sale_price = Decimal("0.00")

            # Aggregate demand per product so duplicate lines cannot oversell.
            requested_by_product: dict[int, int] = {}
            for item in items:
                product_id = item["product_id"]
                requested_by_product[product_id] = (
                    requested_by_product.get(product_id, 0) + item["quantity"]
                )

            locked_products: dict[int, object] = {}
            for product_id in sorted(requested_by_product):
                product = ProductRepository.lock_for_update(self.db, product_id, company_id)
                if not product:
                    raise ResourceNotFoundException(f"Product with ID {product_id} was not found.")
                if not product.is_active:
                    raise ValidationError(f"Product '{product.name}' is inactive.")

                current_stock = StockRepository.get_current_stock(self.db, product_id, store_id)
                requested = requested_by_product[product_id]
                if current_stock < requested:
                    raise InsufficientStockException(
                        f"Not enough stock for '{product.name}'. "
                        f"Available: {current_stock}, requested: {requested}."
                    )
                locked_products[product_id] = product

            for item in items:
                product = locked_products[item["product_id"]]
                quantity = item["quantity"]
                item_total = Decimal(product.sale_price) * Decimal(quantity)
                total_sale_price += item_total
                validated_items.append(
                    {
                        "product": product,
                        "quantity": quantity,
                        "unit_price": product.sale_price,
                    }
                )

            if discount > total_sale_price:
                raise ValidationError("Discount cannot exceed the sale total.")

            final_total = (total_sale_price - discount).quantize(Decimal("0.01"))

            sale = SaleRepository.create(
                self.db,
                company_id=company_id,
                store_id=store_id,
                customer_id=customer_id,
                user_id=user_id,
                total_amount=final_total,
                discount_amount=discount,
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
                details={"discount_amount": str(discount)} if discount else None,
            )

            self.db.commit()
            return self.get_by_id(sale.id, company_id)
        except (
            ValidationError,
            ResourceNotFoundException,
            InsufficientStockException,
            UnauthorizedException,
        ):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessRuleException(f"Sale processing failed. Transaction cancelled: {e}")

    def cancel_sale(
        self,
        sale_id: int,
        *,
        company_id: int,
        actor_id: int,
        supervisor_authorization: str | None = None,
    ) -> Sale:
        sale = SaleRepository.find_by_id(self.db, sale_id, company_id)
        if not sale:
            raise ResourceNotFoundException(f"Sale with ID {sale_id} was not found.")

        if sale.status == SaleStatus.CANCELADA:
            raise ValidationError("Sale is already cancelled.")
        if sale.status == SaleStatus.SUSPENSA:
            raise ValidationError("Suspended sales cannot be cancelled via this endpoint.")

        actor = UserRepository.find_by_id(self.db, actor_id, company_id=company_id)
        if not actor:
            raise ResourceNotFoundException(f"User with ID {actor_id} was not found.")

        self._ensure_cancel_authorized(
            actor=actor,
            supervisor_authorization=supervisor_authorization,
        )

        sale_items = sorted(
            SaleRepository.find_items_by_sale(self.db, sale_id),
            key=lambda item: item.product_id,
        )

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
        except (ValidationError, ResourceNotFoundException, UnauthorizedException):
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

    def _ensure_discount_authorized(
        self, *, actor: User, supervisor_authorization: str | None
    ) -> None:
        if has_permission(actor.profile, "sales:discount"):
            return
        if not supervisor_authorization:
            raise UnauthorizedException("Discount requires Supervisor+ authorization.")
        AuthService(self.db).validate_pdv_authorization(
            token=supervisor_authorization,
            operator=actor,
            required_action="discount",
        )

    def _ensure_cancel_authorized(
        self, *, actor: User, supervisor_authorization: str | None
    ) -> None:
        if has_permission(actor.profile, "sales:cancel"):
            return
        if not supervisor_authorization:
            raise UnauthorizedException(
                "Cancel requires sales:cancel or Supervisor+ authorization."
            )
        AuthService(self.db).validate_pdv_authorization(
            token=supervisor_authorization,
            operator=actor,
            required_action="cancel",
        )
