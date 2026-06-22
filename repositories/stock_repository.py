import sqlite3

class StockRepository:

    @staticmethod
    def find_by_product(cursor: sqlite3.Cursor, product_id: int) -> list:
        query = "SELECT id, product_id, quantity, movement_type, created_at FROM stock_movements WHERE product_id = ?;"
        cursor.execute(query, (product_id,))
        return cursor.fetchall()

    @staticmethod
    def create_movement(cursor: sqlite3.Cursor, product_id: int, quantity: int, movement_type: str) -> int:
        query = "INSERT INTO stock_movements (product_id, quantity, movement_type) VALUES (?, ?, ?);"
        cursor.execute(query, (product_id, quantity, movement_type))
        return cursor.lastrowid

    @staticmethod
    def get_current_stock(cursor: sqlite3.Cursor, product_id: int) -> int:
        # Soma entradas e subtrai saídas com base no tipo, ou assume soma simples se salvar negativo
        query = """
            SELECT COALESCE(SUM(
                CASE WHEN movement_type = 'IN' THEN quantity 
                     WHEN movement_type = 'OUT' THEN -quantity 
                     ELSE 0 END
            ), 0) AS current_stock
            FROM stock_movements 
            WHERE product_id = ?;
        """
        cursor.execute(query, (product_id,))
        result = cursor.fetchone()
        return result[0] if result else 0