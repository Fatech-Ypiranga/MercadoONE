from sqlmodel import Session

from stock.models import StockMovement


class MovementRepository:
    @staticmethod
    def register_movement(db: Session, movement: StockMovement) -> StockMovement:
        """Caller must set company_id and store_id on the movement before calling."""
        db.add(movement)
        db.flush()
        return movement
