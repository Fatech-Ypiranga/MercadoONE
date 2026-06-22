import sqlite3

class CategoryRepository:
    
    @staticmethod
    def find_all(cursor: sqlite3.Cursor) -> list:
        query = "SELECT id, name, description FROM categories;"
        cursor.execute(query)
        return cursor.fetchall()

    @staticmethod
    def find_by_id(cursor: sqlite3.Cursor, category_id: int) -> tuple:
        query = "SELECT id, name, description FROM categories WHERE id = ?;"
        cursor.execute(query, (category_id,))
        return cursor.fetchone()

    @staticmethod
    def create(cursor: sqlite3.Cursor, name: str, description: str) -> int:
        query = "INSERT INTO categories (name, description) VALUES (?, ?);"
        cursor.execute(query, (name, description))
        return cursor.lastrowid

    @staticmethod
    def update(cursor: sqlite3.Cursor, category_id: int, name: str, description: str) -> bool:
        query = "UPDATE categories SET name = ?, description = ? WHERE id = ?;"
        cursor.execute(query, (name, description, category_id))
        return cursor.rowcount > 0

    @staticmethod
    def delete(cursor: sqlite3.Cursor, category_id: int) -> bool:
        query = "DELETE FROM categories WHERE id = ?;"
        cursor.execute(query, (category_id,))
        return cursor.rowcount > 0