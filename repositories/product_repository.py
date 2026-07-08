import sqlite3

class ProductRepository:

    @staticmethod
    def find_all(cursor: sqlite3.Cursor) -> list:
        query = "SELECT id, nome, descricao, preco_venda, categoria_id, estoque_atual, fornecedor_id FROM produtos;"
        cursor.execute(query)
        return cursor.fetchall()

    @staticmethod
    def find_by_id(cursor: sqlite3.Cursor, product_id: int) -> tuple:
        query = "SELECT id, nome, descricao, preco_venda, categoria_id, estoque_atual, fornecedor_id FROM produtos WHERE id = ?;"
        cursor.execute(query, (product_id,))
        return cursor.fetchone()

    @staticmethod
    def find_by_category(cursor: sqlite3.Cursor, category_id: int) -> list:
        query = "SELECT id, nome, descricao, preco_venda, categoria_id, estoque_atual, fornecedor_id FROM produtos WHERE categoria_id = ?;"
        cursor.execute(query, (category_id,))
        return cursor.fetchall()

    @staticmethod
    def create(cursor: sqlite3.Cursor, nome: str, descricao: str, preco_venda: float, categoria_id: int, fornecedor_id: int = None) -> int:
        query = "INSERT INTO produtos (nome, descricao, preco_venda, categoria_id, fornecedor_id) VALUES (?, ?, ?, ?, ?);"
        cursor.execute(query, (nome, descricao, preco_venda, categoria_id, fornecedor_id))
        return cursor.lastrowid

    @staticmethod
    def update(cursor: sqlite3.Cursor, product_id: int, nome: str, descricao: str, preco_venda: float, categoria_id: int, fornecedor_id: int = None) -> bool:
        query = "UPDATE produtos SET nome = ?, descricao = ?, preco_venda = ?, categoria_id = ?, fornecedor_id = ? WHERE id = ?;"
        cursor.execute(query, (nome, descricao, preco_venda, categoria_id, fornecedor_id, product_id))
        return cursor.rowcount > 0

    @staticmethod
    def delete(cursor: sqlite3.Cursor, product_id: int) -> bool:
        query = "DELETE FROM produtos WHERE id = ?;"
        cursor.execute(query, (product_id,))
        return cursor.rowcount > 0