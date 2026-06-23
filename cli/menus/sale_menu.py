import sqlite3
from repositories.customer_repository import CustomerRepository
from repositories.product_repository import ProductRepository
from repositories.sale_repository import SaleRepository
from repositories.stock_repository import StockRepository
from services.sale_service import SaleService
from services.exceptions import ValidationError, ResourceNotFoundException, InsufficientStockException, BusinessRuleException


def sale_menu(conn: sqlite3.Connection):
    while True:
        print("\n------ Vendas ------")
        print("1. Nova venda")
        print("2. Listar vendas")
        print("3. Cadastrar cliente")
        print("0. Voltar")
        print("--------------------")

        option = input("Escolha uma opção: ").strip()

        if option == "1":
            create_sale(conn)
        elif option == "2":
            list_sales(conn)
        elif option == "3":
            create_customer(conn)
        elif option == "0":
            break
        else:
            print("Opção inválida.")


def create_sale(conn: sqlite3.Connection):
    print("\n--- Nova Venda ---")
    cursor = conn.cursor()

    # Selecionar cliente
    print("\nClientes disponíveis:")
    customers = CustomerRepository.find_all(cursor)
    
    if not customers:
        print("Nenhum cliente disponível. Cadastre um cliente primeiro.")
        return

    for c in customers:
        print(f"  [{c[0]}] {c[1]}")

    try:
        customer_id = int(input("ID do cliente (0 para venda sem cliente): "))
    except ValueError:
        print("Entrada inválida.")
        return

    # Se escolher 0, usa consumidor final (customer_id = None)
    if customer_id == 0:
        customer_id = None
    else:
        customer = CustomerRepository.find_by_id(cursor, customer_id)
        if not customer:
            print("Cliente não encontrado.")
            return

    # Montar carrinho
    items = []
    while True:
        print("\n--- Produtos disponíveis ---")
        products = ProductRepository.find_all(cursor)
        
        if not products:
            print("Nenhum produto disponível.")
            break

        for p in products:
            stock = StockRepository.get_current_stock(cursor, p[0])
            print(f"  [{p[0]}] {p[1]:<20} | R$ {p[3]:.2f} | Estoque: {stock}")

        product_input = input("\nID do produto (0 para finalizar): ").strip()
        if product_input == "0":
            break

        try:
            product_id = int(product_input)
            quantity = int(input("Quantidade: "))
        except ValueError:
            print("Entrada inválida.")
            continue

        product = ProductRepository.find_by_id(cursor, product_id)
        if not product:
            print("Produto não encontrado.")
            continue

        stock = StockRepository.get_current_stock(cursor, product_id)
        if stock < quantity:
            print(f"Estoque insuficiente. Disponível: {stock}")
            continue

        items.append({
            "product_id": product_id,
            "quantity": quantity,
        })
        print(f"  ✓ {product[1]} x{quantity} adicionado.")

    if not items:
        print("Nenhum item adicionado. Venda cancelada.")
        return

    # Processar venda através do SaleService
    try:
        sale_id = SaleService.process_sale(conn, customer_id, items)
        
        # Recuperar dados da venda para exibir recibo
        cursor = conn.cursor()  # Reconectar após a transação
        sale = SaleRepository.find_by_id(cursor, sale_id)
        sale_items = SaleRepository.find_items_by_sale(cursor, sale_id)
        
        # Obter nome do cliente
        if customer_id:
            customer = CustomerRepository.find_by_id(cursor, customer_id)
            customer_name = customer[1] if customer else "Desconhecido"
        else:
            customer_name = "Consumidor Final"

        # Exibir recibo
        print(f"\n{'='*35}")
        print(f"  VENDA #{sale_id} — {customer_name}")
        print(f"{'='*35}")
        
        for item in sale_items:
            product = ProductRepository.find_by_id(cursor, item[2])
            subtotal = item[3] * item[4]  # quantity * unit_price
            print(f"  {product[1]:<20} x{item[3]} = R$ {subtotal:.2f}")
        
        print(f"{'='*35}")
        print(f"  TOTAL: R$ {sale[2]:.2f}")
        print(f"{'='*35}")

    except (ValidationError, ResourceNotFoundException, InsufficientStockException, BusinessRuleException) as e:
        print(f"\n❌ Erro na venda: {e}")


def list_sales(conn: sqlite3.Connection):
    print("\n--- Vendas Realizadas ---")
    cursor = conn.cursor()
    
    sales = SaleRepository.find_all(cursor)
    
    if not sales:
        print("Nenhuma venda registrada.")
        return

    for sale in sales:
        sale_id, customer_id, total_price, created_at = sale
        
        # Obter nome do cliente
        if customer_id:
            customer = CustomerRepository.find_by_id(cursor, customer_id)
            customer_name = customer[1] if customer else "Desconhecido"
        else:
            customer_name = "Consumidor Final"
        
        # Contar itens da venda
        items = SaleRepository.find_items_by_sale(cursor, sale_id)
        item_count = len(items)
        
        print(f"Venda #{sale_id} | {customer_name:<20} | {item_count} item(ns) | Total: R$ {total_price:.2f}")



def create_customer(conn: sqlite3.Connection):
    print("\n--- Cadastrar Cliente ---")
    cursor = conn.cursor()
    
    name = input("Nome: ").strip()
    email = input("E-mail: ").strip()
    phone = input("Telefone (opcional): ").strip()

    try:
        new_id = CustomerRepository.create(cursor, name, email, phone)
        conn.commit()
        print(f"Cliente '{name}' cadastrado! (ID: {new_id})")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao cadastrar cliente: {e}")
