import sqlite3

class MovementRepository:
    @staticmethod
    def get_all_movements(cursor: sqlite3.Cursor):
        query = """
            SELECT m.created_at, p.nome, m.movement_type, m.quantity
            FROM stock_movements m
            JOIN produtos p ON m.product_id = p.id
            ORDER BY m.created_at DESC
        """
        cursor.execute(query)
        return cursor.fetchall()
    
    @staticmethod
    def register_movement(cursor: sqlite3.Cursor, product_id: int, quantity: int, movement_type: str):
        query = """
            INSERT INTO stock_movements (product_id, quantity, movement_type)
            VALUES (?, ?, ?)
        """
        cursor.execute(query, (product_id, quantity, movement_type))