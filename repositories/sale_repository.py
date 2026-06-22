import sqlite3

class SaleRepository:

    @staticmethod
    def find_all(cursor: sqlite3.Cursor) -> list:
        query = "SELECT id, customer_id, total_price, created_at FROM sales;"
        cursor.execute(query)
        return cursor.fetchall()

    @staticmethod
    def find_by_id(cursor: sqlite3.Cursor, sale_id: int) -> tuple:
        query = "SELECT id, customer_id, total_price, created_at FROM sales WHERE id = ?;"
        cursor.execute(query, (sale_id,))
        return cursor.fetchone()

    @staticmethod
    def create(cursor: sqlite3.Cursor, customer_id: int, total_price: float) -> int:
        query = "INSERT INTO sales (customer_id, total_price) VALUES (?, ?);"
        cursor.execute(query, (customer_id, total_price))
        return cursor.lastrowid

    @staticmethod
    def find_items_by_sale(cursor: sqlite3.Cursor, sale_id: int) -> list:
        query = "SELECT id, sale_id, product_id, quantity, unit_price FROM sale_items WHERE sale_id = ?;"
        cursor.execute(query, (sale_id,))
        return cursor.fetchall()