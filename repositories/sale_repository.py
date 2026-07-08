import sqlite3

class SaleRepository:

    @staticmethod
    def find_all(cursor: sqlite3.Cursor) -> list:
        query = "SELECT id, cliente_id, usuario_id, data_venda, valor_total, forma_pagamento, status FROM vendas;"
        cursor.execute(query)
        return cursor.fetchall()

    @staticmethod
    def find_by_id(cursor: sqlite3.Cursor, sale_id: int) -> tuple:
        query = "SELECT id, cliente_id, usuario_id, data_venda, valor_total, forma_pagamento, status FROM vendas WHERE id = ?;"
        cursor.execute(query, (sale_id,))
        return cursor.fetchone()

    @staticmethod
    def create(cursor: sqlite3.Cursor, cliente_id: int = None, usuario_id: int = None, valor_total: float = 0.0, forma_pagamento: str = None, status: str = 'Em_Andamento') -> int:
        query = "INSERT INTO vendas (cliente_id, usuario_id, valor_total, forma_pagamento, status) VALUES (?, ?, ?, ?, ?);"
        cursor.execute(query, (cliente_id, usuario_id, valor_total, forma_pagamento, status))
        return cursor.lastrowid

    @staticmethod
    def find_items_by_sale(cursor: sqlite3.Cursor, sale_id: int) -> list:
        query = "SELECT venda_id, produto_id, quantidade, preco_unitario FROM itens_venda WHERE venda_id = ?;"
        cursor.execute(query, (sale_id,))
        return cursor.fetchall()