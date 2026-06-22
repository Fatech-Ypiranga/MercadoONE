import sqlite3
from repositories.sale_repository import SaleRepository
from repositories.stock_repository import StockRepository
from repositories.product_repository import ProductRepository
from repositories.customer_repository import CustomerRepository
from services.exceptions import ValidationError, ResourceNotFoundException, InsufficientStockException, BusinessRuleException

class SaleService:

    @staticmethod
    def process_sale(conn: sqlite3.Connection, customer_id: int, items: list[dict]) -> int:
        """
        items deve ser uma lista de dicionários contendo:
        [{'product_id': 1, 'quantity': 2}, {'product_id': 3, 'quantity': 1}]
        """
        if not items:
            raise ValidationError("Uma venda precisa ter pelo menos um item.")
            
        cursor = conn.cursor()
        
        # 1. Validar cliente
        if not CustomerRepository.find_by_id(cursor, customer_id):
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
                
            # Destrinchando a tupla retornada pelo repositório (ex: id, name, desc, price, cat_id)
            price = product[3]
            
            # Verificar estoque atual
            current_stock = StockRepository.get_current_stock(cursor, pid)
            if current_stock < qty:
                raise InsufficientStockException(
                    f"Estoque insuficiente para o produto '{product[1]}'. Em estoque: {current_stock}, Pedido: {qty}"
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
            # Insere o cabeçalho da venda
            sale_id = SaleRepository.create(cursor, customer_id, total_sale_price)
            
            # Insere cada item e faz a baixa do estoque correspondente
            for v_item in validated_items:
                # Aqui assumimos que seu sale_repository possui a query de insert de itens se necessário,
                # ou você pode executar diretamente via DML isolado aqui. Vamos isolar a query de itens:
                item_query = "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?);"
                cursor.execute(item_query, (sale_id, v_item['product_id'], v_item['quantity'], v_item['unit_price']))
                
                # Baixa automática no estoque gerando uma movimentação do tipo 'OUT'
                StockRepository.create_movement(cursor, v_item['product_id'], v_item['quantity'], 'OUT')
                
            conn.commit()
            return sale_id
            
        except Exception as e:
            conn.rollback()
            raise BusinessRuleException(f"Falha crítica no processamento da venda. Operação cancelada: {e}")