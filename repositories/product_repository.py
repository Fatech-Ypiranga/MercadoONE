import sqlite3

class ProductRepository:

    @staticmethod
    def find_all(cursor: sqlite3.Cursor) -> list:
        query = "SELECT id, name, description, price, category_id FROM products;"
        cursor.execute(query)
        return cursor.fetchall()

    @staticmethod
    def find_by_id(cursor: sqlite3.Cursor, product_id: int) -> tuple:
        query = "SELECT id, name, description, price, category_id FROM products WHERE id = ?;"
        cursor.execute(query, (product_id,))
        return cursor.fetchone()

    @staticmethod
    def find_by_category(cursor: sqlite3.Cursor, category_id: int) -> list:
        query = "SELECT id, name, description, price, category_id FROM products WHERE category_id = ?;"
        cursor.execute(query, (category_id,))
        return cursor.fetchall()

    @staticmethod
    def create(cursor: sqlite3.Cursor, name: str, description: str, price: float, category_id: int) -> int:
        query = "INSERT INTO products (name, description, price, category_id) VALUES (?, ?, ?, ?);"
        cursor.execute(query, (name, description, price, category_id))
        return cursor.lastrowid

    @staticmethod
    def update(cursor: sqlite3.Cursor, product_id: int, name: str, description: str, price: float, category_id: int) -> bool:
        query = "UPDATE products SET name = ?, description = ?, price = ?, category_id = ? WHERE id = ?;"
        cursor.execute(query, (name, description, price, category_id, product_id))
        return cursor.rowcount > 0

    @staticmethod
    def delete(cursor: sqlite3.Cursor, product_id: int) -> bool:
        query = "DELETE FROM products WHERE id = ?;"
        cursor.execute(query, (product_id,))
        return cursor.rowcount > 0