import sqlite3
from repositories.stock_repository import StockRepository
from repositories.product_repository import ProductRepository
from services.exceptions import ValidationError, ResourceNotFoundException, InsufficientStockException, BusinessRuleException

class StockService:

    @staticmethod
    def register_movement(conn: sqlite3.Connection, product_id: int, quantity: int, movement_type: str) -> None:
        cursor = conn.cursor()

        if quantity <= 0:
            raise ValidationError("A quantidade da movimentação deve ser maior que zero.")
        if movement_type not in ('IN', 'OUT'):
            raise ValidationError("Tipo de movimentação inválido. Use 'IN' ou 'OUT'.")

        if not ProductRepository.find_by_id(cursor, product_id):
            raise ResourceNotFoundException(f"Produto com ID {product_id} não encontrado.")

        if movement_type == 'OUT':
            current_stock = StockRepository.get_current_stock(cursor, product_id)
            if current_stock < quantity:
                raise InsufficientStockException(
                    f"Estoque insuficiente. Disponível: {current_stock}, Solicitado: {quantity}."
                )

        try:
            delta = quantity if movement_type == 'IN' else -quantity
            StockRepository.update_stock(cursor, product_id, delta)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise BusinessRuleException(f"Falha na transação de estoque: {e}")