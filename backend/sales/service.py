from datetime import datetime
from decimal import Decimal

from sqlmodel import Session

from auth.service import AuthService
from customers.repository import CustomerRepository
from products.repository import ProductRepository
from sales.models import Sale, SaleStatus
from sales.repository import SaleRepository
from shared.audit import AuditService
from shared.exceptions import (
    BusinessRuleException,
    InsufficientStockException,
    ResourceNotFoundException,
    UnauthorizedException,
    ValidationError,
)
from shared.identity.permissions import has_permission
from stock.models import MovementReason, MovementType, StockMovement
from stock.movement_repository import MovementRepository
from stock.repository import StockRepository
from users.models import User
from users.repository import UserRepository
from utils.enums import AuditAction

MIXED_PAYMENT_METHOD = "multiplo"


class SaleService:
    def __init__(self, db: Session):
        self.db = db

    def process_sale(self, *args, **kwargs) -> Sale:
        return self.process_sale_idempotent(*args, **kwargs)[0]

    def process_sale_idempotent(
        self,
        customer_id: int | None,
        items: list[dict],
        user_id: int,
        *,
        company_id: int,
        client_sale_id: str | None = None,
        **kwargs,
    ) -> tuple[Sale, bool]:
        """Process a sale; returns (sale, created).

        If client_sale_id was already used in this company, the original sale is
        returned with created=False and no stock is moved again.
        """
        if client_sale_id is not None:
            existing = SaleRepository.find_by_client_sale_id(self.db, company_id, client_sale_id)
            if existing:
                return existing, False
        try:
            sale = self._process_new_sale(
                customer_id,
                items,
                user_id,
                company_id=company_id,
                client_sale_id=client_sale_id,
                **kwargs,
            )
            return sale, True
        except Exception:
            if client_sale_id is None:
                raise
            # A concurrent request with the same key may have won the race.
            self.db.rollback()
            existing = SaleRepository.find_by_client_sale_id(self.db, company_id, client_sale_id)
            if existing:
                return existing, False
            raise

    def _process_new_sale(
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
        client_sale_id: str | None = None,
        payments: list[dict] | None = None,
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
            payment_rows = self._resolve_payments(payments, payment_method, final_total)
            if payments is not None:
                payment_method = (
                    payment_rows[0][0] if len(payment_rows) == 1 else MIXED_PAYMENT_METHOD
                )

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
                client_sale_id=client_sale_id,
            )

            for method, amount in payment_rows:
                SaleRepository.add_payment(self.db, sale.id, method, amount)

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

    @staticmethod
    def _resolve_payments(
        payments: list[dict] | None, payment_method: str | None, final_total: Decimal
    ) -> list[tuple[str, Decimal]]:
        """Normalise the payment split; the sum must equal the sale total exactly."""
        if payments is None:
            # Legacy single payment_method: the whole total is paid with it.
            method = (payment_method or "").strip().lower()
            if method and final_total > 0:
                return [(method, final_total)]
            return []

        rows: list[tuple[str, Decimal]] = []
        for payment in payments:
            method = str(payment["method"]).strip().lower()
            amount = Decimal(payment["amount"]).quantize(Decimal("0.01"))
            if not method:
                raise ValidationError("Each payment needs a method.")
            if amount <= 0:
                raise ValidationError("Each payment amount must be greater than zero.")
            rows.append((method, amount))
        paid = sum((amount for _, amount in rows), Decimal("0.00"))
        if paid != final_total:
            raise ValidationError(
                f"Payments total {paid} does not match the sale total {final_total}."
            )
        return rows

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
        return SaleRepository.find_by_id(self.db, sale_id, company_id)

    def list_sales(
        self,
        company_id: int,
        *,
        customer_id: int | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        store_id: int | None = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> tuple[list[Sale], int]:
        sales = SaleRepository.find_filtered(
            self.db,
            company_id,
            customer_id=customer_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            store_id=store_id,
            offset=offset,
            limit=limit,
        )
        total = SaleRepository.count_filtered(
            self.db,
            company_id,
            customer_id=customer_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            store_id=store_id,
        )
        return sales, total

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
