import sqlite3

class StockRepository:

    @staticmethod
    def get_current_stock(cursor: sqlite3.Cursor, product_id: int) -> int:
        """Retorna o estoque atual de um produto"""
        query = "SELECT estoque_atual FROM produtos WHERE id = ?;"
        cursor.execute(query, (product_id,))
        result = cursor.fetchone()
        return result[0] if result else 0

    @staticmethod
    def update_stock(cursor: sqlite3.Cursor, product_id: int, quantidade: int) -> bool:
        """Atualiza o estoque de um produto"""
        query = "UPDATE produtos SET estoque_atual = estoque_atual + ? WHERE id = ?;"
        cursor.execute(query, (quantidade, product_id))
        return cursor.rowcount > 0

    @staticmethod
    def set_stock(cursor: sqlite3.Cursor, product_id: int, quantidade: int) -> bool:
        """Define o estoque para um valor específico"""
        query = "UPDATE produtos SET estoque_atual = ? WHERE id = ?;"
        cursor.execute(query, (quantidade, product_id))
        return cursor.rowcount > 0