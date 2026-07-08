import sqlite3

class CategoryRepository:
    
    @staticmethod
    def find_all(cursor: sqlite3.Cursor) -> list:
        query = "SELECT id, nome, descricao FROM categorias;"
        cursor.execute(query)
        return cursor.fetchall()

    @staticmethod
    def find_by_id(cursor: sqlite3.Cursor, category_id: int) -> tuple:
        query = "SELECT id, nome, descricao FROM categorias WHERE id = ?;"
        cursor.execute(query, (category_id,))
        return cursor.fetchone()

    @staticmethod
    def create(cursor: sqlite3.Cursor, nome: str, descricao: str) -> int:
        query = "INSERT INTO categorias (nome, descricao) VALUES (?, ?);"
        cursor.execute(query, (nome, descricao))
        return cursor.lastrowid

    @staticmethod
    def update(cursor: sqlite3.Cursor, category_id: int, nome: str, descricao: str) -> bool:
        query = "UPDATE categorias SET nome = ?, descricao = ? WHERE id = ?;"
        cursor.execute(query, (nome, descricao, category_id))
        return cursor.rowcount > 0

    @staticmethod
    def delete(cursor: sqlite3.Cursor, category_id: int) -> bool:
        query = "DELETE FROM categorias WHERE id = ?;"
        cursor.execute(query, (category_id,))
        return cursor.rowcount > 0