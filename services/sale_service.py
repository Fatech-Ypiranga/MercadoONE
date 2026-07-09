import sqlite3
from repositories.sale_repository import SaleRepository
from repositories.stock_repository import StockRepository
from repositories.product_repository import ProductRepository
from repositories.customer_repository import CustomerRepository
from services.exceptions import ValidationError, ResourceNotFoundException, InsufficientStockException, BusinessRuleException
from repositories.movement_repository import MovementRepository


class SaleService:

    @staticmethod
    def process_sale(conn: sqlite3.Connection, customer_id: int | None, items: list[dict]) -> int:
        """
        items deve ser uma lista de dicionários contendo:
        [{'product_id': 1, 'quantity': 2}, {'product_id': 3, 'quantity': 1}]
        """
        if not items:
            raise ValidationError("Uma venda precisa ter pelo menos um item.")

        cursor = conn.cursor()

        # 1. Validar cliente quando houver um cliente informado
        if customer_id is not None and not CustomerRepository.find_by_id(cursor, customer_id):
            raise ResourceNotFoundException(f"Cliente com ID {customer_id} não encontrado.")

        total_sale_price = 0.0
        validated_items = []

        # 2. Pré-validação de estoque e preços para evitar falhas parciais
        for item in items:
            pid = item['product_id']
            qty = item['quantity']

            if qty <= 0:
                raise ValidationError("A quantidade de cada item deve ser maior que zero.")

            product = ProductRepository.find_by_id(cursor, pid)
            if not product:
                raise ResourceNotFoundException(f"Produto ID {pid} não encontrado no catálogo.")

            price = product[3] if not isinstance(product, sqlite3.Row) else product["preco_venda"]
            product_name = product[1] if not isinstance(product, sqlite3.Row) else product["nome"]

            current_stock = StockRepository.get_current_stock(cursor, pid)
            if current_stock < qty:
                raise InsufficientStockException(
                    f"Estoque insuficiente para o produto '{product_name}'. Em estoque: {current_stock}, Pedido: {qty}"
                )

            item_total = price * qty
            total_sale_price += item_total

            validated_items.append({
                'product_id': pid,
                'quantity': qty,
                'unit_price': price
            })

        # 3. Processamento Atômico (Gravação das Tabelas)
        try:
            sale_id = SaleRepository.create(
                cursor,
                cliente_id=customer_id,
                usuario_id=None,
                valor_total=total_sale_price,
                forma_pagamento=None,
                status='Em_Andamento'
            )

            for v_item in validated_items:
            # Insere o item da venda
             item_query = "INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?);"

            cursor.execute(item_query, (sale_id, v_item['product_id'], v_item['quantity'], v_item['unit_price']))
            
            # Atualiza o estoque
            StockRepository.update_stock(cursor, v_item['product_id'], -v_item['quantity'])
            
            # REGISTRA NO HISTÓRICO DE MOVIMENTAÇÃO (SAÍDA)
            MovementRepository.register_movement(cursor, v_item['product_id'], v_item['quantity'], 'OUT')

            conn.commit()
            return sale_id

        except Exception as e:
            conn.rollback()
            raise BusinessRuleException(f"Falha crítica no processamento da venda. Operação cancelada: {e}")