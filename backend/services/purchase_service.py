from datetime import datetime, timezone
from decimal import Decimal

from pydantic import ValidationError as PydanticValidationError
from sqlmodel import Session

from models.product import Product, ProductCreate, ProductFiscalCreate, UnitOfMeasure
from models.purchase import (
    NfeInvoicePreview,
    NfeItemPreview,
    NfeSupplierAddressPreview,
    NfeSupplierPreview,
    NfeUploadPreviewResponse,
    PurchaseConfirmItemInput,
    PurchaseConfirmRequest,
    PurchaseItem,
    PurchaseItemResponse,
    PurchaseOrder,
    PurchaseOrderDetailResponse,
    PurchaseOrderResponse,
    SupplierProductMapping,
)
from models.stock_movement import MovementReason, MovementType, StockMovement
from repositories.movement_repository import MovementRepository
from repositories.product_repository import ProductRepository
from repositories.purchase_repository import PurchaseRepository, SupplierMappingRepository
from repositories.stock_repository import StockRepository
from services.exceptions import (
    BusinessRuleException,
    ConflictException,
    InsufficientStockException,
    ResourceNotFoundException,
    ValidationError,
)
from services.nfe_parser import ParsedNfeItem, calculate_entry_unit_cost, parse_nfe_xml
from services.product_service import ProductService
from shared.audit import AuditService
from suppliers.models import Supplier, SupplierAddressCreate, SupplierCreate
from suppliers.repository import SupplierRepository
from suppliers.service import SupplierService
from utils.cnpj import normalize_cnpj
from utils.enums import AuditAction, PurchaseStatus


class PurchaseService:
    def __init__(self, db: Session):
        self.db = db

    def preview_xml_upload(
        self, xml_content: str | bytes, *, company_id: int
    ) -> NfeUploadPreviewResponse:
        parsed = parse_nfe_xml(xml_content)
        supplier = SupplierRepository.find_by_document(
            self.db, normalize_cnpj(parsed.supplier.document), company_id
        )
        items = [
            self._build_item_preview(parsed_item, supplier.id if supplier else None, company_id)
            for parsed_item in parsed.items
        ]

        return NfeUploadPreviewResponse(
            supplier=NfeSupplierPreview(
                document=parsed.supplier.document,
                name=parsed.supplier.name,
                trade_name=parsed.supplier.trade_name,
                state_registration=parsed.supplier.state_registration,
                address=NfeSupplierAddressPreview(**vars(parsed.supplier.address)),
                exists_in_database=supplier is not None,
                supplier_id=supplier.id if supplier else None,
            ),
            invoice=NfeInvoicePreview(
                access_key=parsed.invoice.access_key,
                invoice_number=parsed.invoice.invoice_number,
                invoice_series=parsed.invoice.invoice_series,
                issue_date=parsed.invoice.issue_date,
                total_amount=parsed.invoice.total_amount,
            ),
            items=items,
        )

    def confirm_purchase(
        self,
        payload: PurchaseConfirmRequest,
        *,
        actor_id: int,
        company_id: int,
        store_id: int,
    ) -> PurchaseOrderDetailResponse:
        if payload.supplier_id is not None and payload.create_supplier:
            raise ValidationError(
                "supplier_id and create_supplier=true cannot be provided together."
            )
        if PurchaseRepository.find_by_invoice_key(self.db, payload.access_key, company_id):
            raise ValidationError(f"Purchase with invoice key {payload.access_key} already exists.")

        if not payload.items:
            raise ValidationError("Purchase confirmation requires at least one item.")

        try:
            supplier = self._resolve_supplier(payload, actor_id=actor_id, company_id=company_id)

            purchase = PurchaseOrder(
                company_id=company_id,
                store_id=store_id,
                supplier_id=supplier.id,
                user_id=actor_id,
                invoice_number=payload.invoice_number,
                invoice_series=payload.invoice_series,
                invoice_key=payload.access_key,
                issue_date=payload.issue_date,
                entry_date=datetime.now(timezone.utc),
                total_amount=Decimal("0.00"),
                status=PurchaseStatus.CONFIRMADO,
                xml_path=payload.xml_path,
                created_by=actor_id,
                updated_by=actor_id,
            )
            PurchaseRepository.create(self.db, purchase)

            total_amount = Decimal("0.00")
            for confirm_item in payload.items:
                product = self._resolve_product(
                    confirm_item,
                    supplier=supplier,
                    actor_id=actor_id,
                    company_id=company_id,
                )

                PurchaseRepository.add_item(
                    self.db,
                    PurchaseItem(
                        purchase_order_id=purchase.id,
                        product_id=product.id,
                        supplier_product_code=confirm_item.supplier_product_code,
                        quantity=confirm_item.quantity,
                        unit_cost=confirm_item.unit_cost,
                        discount=confirm_item.discount,
                        ipi_amount=confirm_item.ipi_amount,
                        icms_st_amount=confirm_item.icms_st_amount,
                        total_cost=confirm_item.total_cost,
                    ),
                )

                self._register_stock_entry(
                    product_id=product.id,
                    quantity=confirm_item.quantity,
                    invoice_number=payload.invoice_number,
                    supplier_name=supplier.name,
                    actor_id=actor_id,
                    company_id=company_id,
                    store_id=store_id,
                )
                self._update_weighted_average_cost(
                    product=product,
                    quantity=confirm_item.quantity,
                    entry_unit_cost=confirm_item.unit_cost,
                    store_id=store_id,
                )
                total_amount += confirm_item.total_cost

            purchase.total_amount = total_amount
            purchase.updated_at = datetime.now(timezone.utc)
            self.db.add(purchase)

            AuditService(self.db).log(
                user_id=actor_id,
                company_id=company_id,
                action=AuditAction.CREATE,
                entity_type="purchase_order",
                entity_id=purchase.id,
                details={"invoice_key": payload.access_key, "supplier_id": supplier.id},
            )

            self.db.commit()
            return self.get_purchase_detail(purchase.id, company_id)
        except (
            ValidationError,
            ResourceNotFoundException,
            InsufficientStockException,
            ConflictException,
        ):
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            raise BusinessRuleException(f"Error confirming purchase: {exc}") from exc

    def confirm_purchase_from_xml(
        self,
        xml_content: str | bytes,
        item_resolutions: list[PurchaseConfirmItemInput],
        *,
        actor_id: int,
        company_id: int,
        store_id: int,
        xml_path: str | None = None,
    ) -> PurchaseOrderDetailResponse:
        parsed = parse_nfe_xml(xml_content)
        preview = self.preview_xml_upload(xml_content, company_id=company_id)
        preview_by_code = {item.supplier_product_code: item for item in preview.items}

        if len(item_resolutions) != len(parsed.items):
            raise ValidationError("Item resolutions must match the number of XML lines.")

        merged_items: list[PurchaseConfirmItemInput] = []
        for resolution in item_resolutions:
            if resolution.supplier_product_code not in preview_by_code:
                raise ValidationError(
                    f"Unknown supplier product code: {resolution.supplier_product_code}"
                )
            preview_item = preview_by_code[resolution.supplier_product_code]
            merged_items.append(
                PurchaseConfirmItemInput(
                    supplier_product_code=resolution.supplier_product_code,
                    quantity=preview_item.quantity,
                    unit_cost=preview_item.entry_unit_cost,
                    discount=preview_item.discount,
                    ipi_amount=preview_item.ipi_amount,
                    icms_st_amount=preview_item.icms_st_amount,
                    total_cost=preview_item.total_cost,
                    product_id=resolution.product_id,
                    create_product=resolution.create_product,
                )
            )

        supplier = SupplierRepository.find_by_document(
            self.db, normalize_cnpj(parsed.supplier.document), company_id
        )
        supplier_address = None
        if supplier is None:
            try:
                supplier_address = SupplierAddressCreate.model_validate(
                    vars(parsed.supplier.address)
                )
            except PydanticValidationError as exc:
                raise ValidationError(
                    "A complete valid supplier address is required to confirm this NF-e."
                ) from exc
        payload = PurchaseConfirmRequest(
            access_key=parsed.invoice.access_key,
            invoice_number=parsed.invoice.invoice_number,
            invoice_series=parsed.invoice.invoice_series,
            issue_date=parsed.invoice.issue_date,
            supplier_id=supplier.id if supplier else None,
            create_supplier=supplier is None,
            supplier_name=parsed.supplier.name,
            supplier_trade_name=parsed.supplier.trade_name,
            supplier_document=parsed.supplier.document,
            supplier_state_registration=parsed.supplier.state_registration,
            supplier_address=supplier_address,
            items=merged_items,
            xml_path=xml_path,
        )
        return self.confirm_purchase(
            payload, actor_id=actor_id, company_id=company_id, store_id=store_id
        )

    def list_purchases(
        self,
        company_id: int,
        *,
        supplier_id: int | None = None,
        status: PurchaseStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        store_id: int | None = None,
    ) -> list[PurchaseOrderResponse]:
        purchases = PurchaseRepository.find_all(
            self.db,
            company_id,
            supplier_id=supplier_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            store_id=store_id,
        )
        responses: list[PurchaseOrderResponse] = []
        for purchase in purchases:
            supplier = SupplierRepository.find_by_id(self.db, purchase.supplier_id, company_id)
            response = PurchaseOrderResponse.model_validate(purchase)
            response.supplier_name = supplier.name if supplier else None
            responses.append(response)
        return responses

    def get_purchase_detail(self, purchase_id: int, company_id: int) -> PurchaseOrderDetailResponse:
        purchase = PurchaseRepository.find_by_id(self.db, purchase_id, company_id)
        if not purchase:
            raise ResourceNotFoundException(f"Purchase with ID {purchase_id} was not found.")

        supplier = SupplierRepository.find_by_id(self.db, purchase.supplier_id, company_id)
        item_responses: list[PurchaseItemResponse] = []
        for item in purchase.items:
            product = ProductRepository.find_by_id(self.db, item.product_id, company_id)
            item_responses.append(
                PurchaseItemResponse(
                    **item.model_dump(),
                    product_name=product.name if product else None,
                )
            )

        detail = PurchaseOrderDetailResponse.model_validate(purchase)
        detail.supplier_name = supplier.name if supplier else None
        detail.items = item_responses
        return detail

    def cancel_purchase(
        self, purchase_id: int, *, company_id: int, actor_id: int
    ) -> PurchaseOrderDetailResponse:
        purchase = PurchaseRepository.find_by_id(self.db, purchase_id, company_id)
        if not purchase:
            raise ResourceNotFoundException(f"Purchase with ID {purchase_id} was not found.")
        if purchase.status == PurchaseStatus.CANCELADO:
            raise ValidationError("Purchase is already cancelled.")
        if purchase.status != PurchaseStatus.CONFIRMADO:
            raise ValidationError("Only confirmed purchases can be cancelled.")

        supplier = SupplierRepository.find_by_id(self.db, purchase.supplier_id, company_id)
        try:
            items = sorted(purchase.items, key=lambda item: item.product_id)
            for item in items:
                product = ProductRepository.lock_for_update(self.db, item.product_id, company_id)
                current_stock = StockRepository.get_current_stock(
                    self.db, item.product_id, purchase.store_id
                )
                if current_stock < item.quantity:
                    product_name = product.name if product else str(item.product_id)
                    raise InsufficientStockException(
                        f"Cannot cancel purchase: insufficient stock to reverse item '{product_name}'."
                    )

                movement = StockMovement(
                    company_id=purchase.company_id,
                    store_id=purchase.store_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    type=MovementType.SAIDA,
                    reason=MovementReason.DEVOLUCAO,
                    observations=(
                        f"Estorno NF-e nº {purchase.invoice_number}, Fornecedor {supplier.name if supplier else purchase.supplier_id}"
                    ),
                    created_by=actor_id,
                    updated_by=actor_id,
                )
                MovementRepository.register_movement(self.db, movement)
                AuditService(self.db).log(
                    user_id=actor_id,
                    company_id=company_id,
                    action=AuditAction.STOCK_MOVE,
                    entity_type="stock_movement",
                    entity_id=movement.id,
                )

            purchase.status = PurchaseStatus.CANCELADO
            purchase.updated_at = datetime.now(timezone.utc)
            purchase.updated_by = actor_id
            self.db.add(purchase)

            AuditService(self.db).log(
                user_id=actor_id,
                company_id=company_id,
                action=AuditAction.UPDATE,
                entity_type="purchase_order",
                entity_id=purchase_id,
                details={"status": PurchaseStatus.CANCELADO.value},
            )

            self.db.commit()
            return self.get_purchase_detail(purchase_id, company_id)
        except (ValidationError, InsufficientStockException, ResourceNotFoundException):
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            raise BusinessRuleException(f"Error cancelling purchase: {exc}") from exc

    def _build_item_preview(
        self, item: ParsedNfeItem, supplier_id: int | None, company_id: int
    ) -> NfeItemPreview:
        entry_unit_cost = calculate_entry_unit_cost(item)
        total_cost = (
            item.product_total - item.discount + item.ipi_amount + item.icms_st_amount
        ).quantize(Decimal("0.01"))
        product = self._find_product_for_item(item, supplier_id, company_id)

        return NfeItemPreview(
            line_number=item.line_number,
            supplier_product_code=item.supplier_product_code,
            barcode=item.barcode,
            name=item.name,
            ncm=item.ncm,
            unit=item.unit,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            discount=item.discount,
            ipi_amount=item.ipi_amount,
            icms_st_amount=item.icms_st_amount,
            entry_unit_cost=entry_unit_cost,
            total_cost=total_cost,
            mapping_status="mapped" if product else "unmapped",
            suggested_product_id=product.id if product else None,
            suggested_product_name=product.name if product else None,
        )

    def _find_product_for_item(
        self, item: ParsedNfeItem, supplier_id: int | None, company_id: int
    ) -> Product | None:
        if supplier_id is not None:
            mapping = SupplierMappingRepository.find_mapping(
                self.db, supplier_id, item.supplier_product_code
            )
            if mapping:
                product = ProductRepository.find_by_id(self.db, mapping.product_id, company_id)
                if product and product.is_active:
                    return product

        if item.barcode:
            product = ProductRepository.find_by_barcode(self.db, item.barcode, company_id)
            if product:
                return product

        return ProductRepository.find_by_sku(self.db, item.supplier_product_code, company_id)

    def _resolve_supplier(
        self, payload: PurchaseConfirmRequest, *, actor_id: int, company_id: int
    ) -> Supplier:
        if payload.supplier_id is not None:
            supplier = SupplierRepository.find_by_id(self.db, payload.supplier_id, company_id)
            if not supplier:
                raise ResourceNotFoundException(
                    f"Supplier with ID {payload.supplier_id} was not found."
                )
            return supplier

        if payload.create_supplier:
            if not payload.supplier_document or not payload.supplier_name:
                raise ValidationError(
                    "Supplier name and document are required to create a new supplier."
                )
            document = normalize_cnpj(payload.supplier_document)
            existing = SupplierRepository.find_by_document(self.db, document, company_id)
            if existing:
                return existing

            if payload.supplier_address is None:
                raise ValidationError(
                    "A complete valid supplier address is required to create a supplier."
                )
            try:
                supplier_in = SupplierCreate(
                    name=payload.supplier_name,
                    trade_name=payload.supplier_trade_name,
                    document=payload.supplier_document,
                    state_registration=payload.supplier_state_registration,
                    address=payload.supplier_address,
                )
            except PydanticValidationError as exc:
                raise ValidationError(f"Invalid supplier data: {exc}") from exc
            return SupplierService(self.db).create(
                supplier_in,
                company_id=company_id,
                actor_id=actor_id,
                commit=False,
            )

        raise ValidationError("supplier_id or create_supplier must be provided.")

    def _resolve_product(
        self,
        confirm_item: PurchaseConfirmItemInput,
        *,
        supplier: Supplier,
        actor_id: int,
        company_id: int,
    ) -> Product:
        if confirm_item.product_id is not None:
            product = ProductRepository.find_by_id(self.db, confirm_item.product_id, company_id)
            if not product:
                raise ResourceNotFoundException(
                    f"Product with ID {confirm_item.product_id} was not found."
                )
            self._ensure_mapping(supplier.id, confirm_item.supplier_product_code, product.id)
            return product

        if confirm_item.create_product is not None:
            create_data = confirm_item.create_product
            sale_price = create_data.sale_price
            if sale_price is None:
                sale_price = (create_data.cost_price * Decimal("1.35")).quantize(Decimal("0.01"))

            unit = UnitOfMeasure.UN
            try:
                unit = UnitOfMeasure(create_data.unit_of_measure)
            except ValueError:
                unit = UnitOfMeasure.UN

            fiscal = None
            if create_data.ncm:
                fiscal = ProductFiscalCreate(
                    ncm=create_data.ncm,
                    cfop_default="5102",
                    origem_produto=0,
                )

            product = ProductService(self.db).create(
                ProductCreate(
                    name=create_data.name,
                    sku=create_data.sku,
                    barcode=create_data.barcode,
                    cost_price=create_data.cost_price,
                    sale_price=sale_price,
                    unit_of_measure=unit,
                    category_id=create_data.category_id,
                    primary_supplier_id=supplier.id,
                    fiscal=fiscal,
                ),
                company_id=company_id,
                actor_id=actor_id,
                commit=False,
            )

            self._ensure_mapping(supplier.id, confirm_item.supplier_product_code, product.id)
            return product

        raise ValidationError(
            f"Item {confirm_item.supplier_product_code} is unmapped. Provide product_id or create_product."
        )

    def _ensure_mapping(
        self, supplier_id: int, supplier_product_code: str, product_id: int
    ) -> None:
        existing = SupplierMappingRepository.find_mapping(
            self.db, supplier_id, supplier_product_code
        )
        if existing:
            return
        SupplierMappingRepository.create(
            self.db,
            SupplierProductMapping(
                supplier_id=supplier_id,
                supplier_product_code=supplier_product_code,
                product_id=product_id,
            ),
        )

    def _register_stock_entry(
        self,
        *,
        product_id: int,
        quantity: Decimal,
        invoice_number: str | None,
        supplier_name: str,
        actor_id: int,
        company_id: int,
        store_id: int,
    ) -> None:
        movement = StockMovement(
            company_id=company_id,
            store_id=store_id,
            product_id=product_id,
            quantity=quantity,
            type=MovementType.ENTRADA,
            reason=MovementReason.COMPRA,
            observations=f"Entrada via NF-e nº {invoice_number}, Fornecedor {supplier_name}",
            created_by=actor_id,
            updated_by=actor_id,
        )
        MovementRepository.register_movement(self.db, movement)
        AuditService(self.db).log(
            user_id=actor_id,
            company_id=company_id,
            action=AuditAction.STOCK_MOVE,
            entity_type="stock_movement",
            entity_id=movement.id,
        )

    def _update_weighted_average_cost(
        self,
        *,
        product: Product,
        quantity: Decimal,
        entry_unit_cost: Decimal,
        store_id: int,
    ) -> None:
        # cost_price is company-global; weight against company-wide stock (not one store).
        _ = store_id
        current_stock = StockRepository.get_current_stock_company(
            self.db, product.id, product.company_id
        )
        previous_stock = current_stock - quantity
        current_cost = Decimal(product.cost_price)

        if previous_stock <= 0:
            new_cost = entry_unit_cost
        else:
            numerator = (previous_stock * current_cost) + (quantity * entry_unit_cost)
            denominator = previous_stock + quantity
            new_cost = (numerator / denominator).quantize(Decimal("0.01"))

        product.cost_price = new_cost
        product.updated_at = datetime.now(timezone.utc)
        self.db.add(product)
