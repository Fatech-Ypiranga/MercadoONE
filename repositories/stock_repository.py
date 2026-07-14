from decimal import Decimal

from sqlmodel import Session, func, select

from models.stock_movement import MovementType, StockMovement


class StockRepository:
    @staticmethod
    def get_current_stock(db: Session, product_id: int, store_id: int) -> Decimal:
        entries_stmt = select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
            StockMovement.product_id == product_id,
            StockMovement.store_id == store_id,
            StockMovement.type == MovementType.ENTRADA,
        )
        exits_stmt = select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
            StockMovement.product_id == product_id,
            StockMovement.store_id == store_id,
            StockMovement.type == MovementType.SAIDA,
        )

        entries = db.exec(entries_stmt).one()
        exits = db.exec(exits_stmt).one()
        return Decimal(entries or 0) - Decimal(exits or 0)
