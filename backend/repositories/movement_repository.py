from sqlmodel import Session, select

from models.stock_movement import StockMovement


class MovementRepository:
    @staticmethod
    def get_all_movements(
        db: Session, company_id: int, *, store_id: int | None = None
    ) -> list[StockMovement]:
        stmt = (
            select(StockMovement)
            .where(StockMovement.company_id == company_id)
            .order_by(StockMovement.created_at.desc())
        )
        if store_id is not None:
            stmt = stmt.where(StockMovement.store_id == store_id)
        return list(db.exec(stmt).all())

    @staticmethod
    def register_movement(db: Session, movement: StockMovement) -> StockMovement:
        """Caller must set company_id and store_id on the movement before calling."""
        db.add(movement)
        db.flush()
        return movement
