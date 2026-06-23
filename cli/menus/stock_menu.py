import sqlite3
from repositories.product_repository import ProductRepository
from repositories.stock_repository import StockRepository


def stock_menu(conn: sqlite3.Connection):
    while True:
        print("\n------ Estoque ------")
        print("1. Ver estoque atual")
        print("2. Registrar entrada")
        print("3. Registrar saída")
        print("4. Ver histórico de movimentações")
        print("0. Voltar")
        print("---------------------")

        option = input("Escolha uma opção: ").strip()

        if option == "1":
            show_stock(conn)
        elif option == "2":
            register_movement(conn, "IN")
        elif option == "3":
            register_movement(conn, "OUT")
        elif option == "4":
            show_movements(conn)
        elif option == "0":
            break
        else:
            print("Opção inválida.")


def show_stock(conn: sqlite3.Connection):
    print("\n--- Estoque Atual ---")
    cursor = conn.cursor()
    
    products = ProductRepository.find_all(cursor)
    
    if not products:
        print("Nenhum produto cadastrado.")
        return

    for p in products:
        product_id = p[0]
        product_name = p[1]
        stock = StockRepository.get_current_stock(cursor, product_id)
        status = "⚠ BAIXO" if stock < 15 else "OK"
        print(f"[{product_id}] {product_name:<20} | Qtd: {stock:>4} | {status}")


def register_movement(conn: sqlite3.Connection, movement_type: str):
    cursor = conn.cursor()
    
    show_stock(conn)
    
    try:
        product_id = int(input("\nID do produto: "))
        quantity = int(input("Quantidade: "))
    except ValueError:
        print("Entrada inválida.")
        return

    product = ProductRepository.find_by_id(cursor, product_id)

    if not product:
        print("Produto não encontrado.")
        return

    # Verificar estoque se for saída
    if movement_type == "OUT":
        current_stock = StockRepository.get_current_stock(cursor, product_id)
        if current_stock < quantity:
            print(f"Estoque insuficiente. Disponível: {current_stock}")
            return

    try:
        StockRepository.create_movement(cursor, product_id, quantity, movement_type)
        conn.commit()
        
        new_stock = StockRepository.get_current_stock(cursor, product_id)
        movement_desc = "ENTRADA" if movement_type == "IN" else "SAÍDA"
        print(f"\n✓ Movimentação ({movement_desc}) registrada! Estoque atual de '{product[1]}': {new_stock}")
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erro ao registrar movimentação: {e}")


def show_movements(conn: sqlite3.Connection):
    print("\n--- Histórico de Movimentações ---")
    cursor = conn.cursor()
    
    # Buscar todos os produtos
    products = ProductRepository.find_all(cursor)
    
    if not products:
        print("Nenhum produto cadastrado.")
        return
    
    movements_exist = False
    
    for p in products:
        product_id = p[0]
        product_name = p[1]
        
        movements = StockRepository.find_by_product(cursor, product_id)
        
        if movements:
            movements_exist = True
            print(f"\n📦 {product_name}:")
            for m in movements:
                arrow = "▲ ENTRADA" if m[3] == "IN" else "▼ SAÍDA"
                print(f"  {arrow} | Qtd: {m[2]:>4} | Data: {m[4]}")
    
    if not movements_exist:
        print("Nenhuma movimentação registrada.")
