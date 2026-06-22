import sqlite3

class ReportService:

    @staticmethod
    def get_top_selling_products(cursor: sqlite3.Cursor, limit: int = 5) -> list:
        """Retorna os produtos mais vendidos por quantidade acumulada."""
        query = """
            SELECT p.id, p.name, SUM(si.quantity) as total_sold
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            GROUP BY p.id
            ORDER BY total_sold DESC
            LIMIT ?;
        """
        cursor.execute(query, (limit,))
        return cursor.fetchall()

    @staticmethod
    def get_average_ticket(cursor: sqlite3.Cursor) -> float:
        """Calcula o valor médio gasto por venda."""
        query = "SELECT COALESCE(AVG(total_price), 0.0) FROM sales;"
        cursor.execute(query)
        result = cursor.fetchone()
        return result[0]

    @staticmethod
    def get_critical_stock_products(cursor: sqlite3.Cursor, min_threshold: int = 5) -> list:
        """Identifica produtos cujo saldo atual em estoque está abaixo do limite de segurança."""
        # Esta query calcula o saldo atual agregando as movimentações e filtra os menores que o limite
        query = """
            SELECT p.id, p.name, 
                   COALESCE(SUM(
                       CASE WHEN sm.movement_type = 'IN' THEN sm.quantity 
                            WHEN sm.movement_type = 'OUT' THEN -sm.quantity 
                            ELSE 0 END
                   ), 0) AS current_stock
            FROM products p
            LEFT JOIN stock_movements sm ON p.id = sm.product_id
            GROUP BY p.id
            HAVING current_stock < ?
            ORDER BY current_stock ASC;
        """
        cursor.execute(query, (min_threshold,))
        return cursor.fetchall()