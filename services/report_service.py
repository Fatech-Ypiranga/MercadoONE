import sqlite3

class ReportService:

    @staticmethod
    def get_top_selling_products(cursor: sqlite3.Cursor, limit: int = 5) -> list:
        """Retorna os produtos mais vendidos por quantidade acumulada."""
        query = """
            SELECT p.id, p.nome, SUM(iv.quantidade) as total_sold
            FROM itens_venda iv
            JOIN produtos p ON iv.produto_id = p.id
            GROUP BY p.id
            ORDER BY total_sold DESC
            LIMIT ?;
        """
        cursor.execute(query, (limit,))
        return cursor.fetchall()

    @staticmethod
    def get_average_ticket(cursor: sqlite3.Cursor) -> float:
        """Calcula o valor médio gasto por venda."""
        query = "SELECT COALESCE(AVG(valor_total), 0.0) FROM vendas;"
        cursor.execute(query)
        result = cursor.fetchone()
        return result[0]

    @staticmethod
    def get_critical_stock_products(cursor: sqlite3.Cursor, min_threshold: int = 5) -> list:
        """Identifica produtos cujo saldo atual em estoque está abaixo do limite de segurança."""
        query = """
            SELECT p.id, p.nome, p.estoque_atual AS current_stock
            FROM produtos p
            WHERE p.estoque_atual < ?
            ORDER BY p.estoque_atual ASC;
        """
        cursor.execute(query, (min_threshold,))
        return cursor.fetchall()