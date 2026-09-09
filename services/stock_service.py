from decimal import Decimal

from sqlmodel import Session, select

from models.stock_movement import MovementType, StockMovement, StockMovementCreate
from repositories.product_repository import ProductRepository
from repositories.stock_repository import StockRepository
from shared.audit import AuditService
from utils.enums import AuditAction


class StockMovementService:
    def __init__(self, db: Session):
        self.db = db

    def create_movement(
        self,
        movement_in: StockMovementCreate,
        *,
        company_id: int,
        store_id: int,
        actor_id: int | None = None,
    ) -> StockMovement | None:
        product = ProductRepository.lock_for_update(self.db, movement_in.product_id, company_id)
        if not product:
            return None

        if movement_in.type == MovementType.SAIDA:
            current_balance = self.get_current_balance(movement_in.product_id, store_id)
            if current_balance < movement_in.quantity:
                return None

        try:
            payload = movement_in.model_dump(exclude={"store_id"})
            db_movement = StockMovement(
                **payload,
                company_id=company_id,
                store_id=store_id,
            )
            if actor_id is not None:
                db_movement.created_by = actor_id
                db_movement.updated_by = actor_id
            self.db.add(db_movement)
            self.db.flush()

            if actor_id is not None:
                AuditService(self.db).log(
                    user_id=actor_id,
                    company_id=company_id,
                    action=AuditAction.STOCK_MOVE,
                    entity_type="stock_movement",
                    entity_id=db_movement.id,
                )

            self.db.commit()
            self.db.refresh(db_movement)
            return db_movement
        except Exception:
            self.db.rollback()
            raise

    def get_current_balance(
        self, product_id: int, store_id: int, *, company_id: int | None = None
    ) -> Decimal:
        if company_id is not None:
            product = ProductRepository.find_by_id(self.db, product_id, company_id)
            if not product:
                return Decimal("0")
        return StockRepository.get_current_stock(self.db, product_id, store_id)

    def get_extract_by_product(
        self,
        product_id: int,
        company_id: int,
        *,
        store_id: int | None = None,
    ):
        stmt = (
            select(StockMovement)
            .where(
                StockMovement.product_id == product_id,
                StockMovement.company_id == company_id,
            )
            .order_by(StockMovement.created_at.desc())
        )
        if store_id is not None:
            stmt = stmt.where(StockMovement.store_id == store_id)
        return self.db.exec(stmt).all()
