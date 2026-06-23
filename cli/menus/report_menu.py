import sqlite3
from services.report_service import ReportService


def report_menu(conn: sqlite3.Connection):
    while True:
        print("\n------ Relatórios ------")
        print("1. Top 5 produtos mais vendidos")
        print("2. Ticket médio por venda")
        print("3. Estoque crítico")
        print("4. Resumo geral")
        print("0. Voltar")
        print("------------------------")

        option = input("Escolha uma opção: ").strip()

        if option == "1":
            top_products(conn)
        elif option == "2":
            average_ticket(conn)
        elif option == "3":
            critical_stock(conn)
        elif option == "4":
            general_summary(conn)
        elif option == "0":
            break
        else:
            print("Opção inválida.")


def top_products(conn: sqlite3.Connection):
    print("\n--- Top 5 Produtos Mais Vendidos ---")
    cursor = conn.cursor()
    
    ranking = ReportService.get_top_selling_products(cursor, limit=5)

    if not ranking:
        print("Nenhuma venda registrada ainda.")
        return
    
    for i, (p_id, name, qty) in enumerate(ranking, start=1):
        print(f"  {i}º [{p_id}] {name:<22} — {qty} unidades vendidas")



def average_ticket(conn: sqlite3.Connection):
    print("\n--- Ticket Médio por Venda ---")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM sales;")
    total_sales = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(total_price), 0.0) FROM sales;")
    total_revenue = cursor.fetchone()[0]


    avg = ReportService.get_average_ticket(cursor)

    print(f"  Vendas realizadas : {total_sales}")
    print(f"  Receita total     : R$ {total_revenue:.2f}")
    print(f"  Ticket médio      : R$ {avg:.2f}")


def critical_stock(conn: sqlite3.Connection):
    MIN_STOCK = 15
    print(f"\n--- Estoque Crítico (abaixo de {MIN_STOCK} unidades) ---")
    cursor = conn.cursor()

    critical = ReportService.get_critical_stock_products(cursor, min_threshold=MIN_STOCK)

    if not critical:
        print("  Nenhum produto em situação crítica.")
        return

    for p_id, name, stock in critical:
        print(f"  ⚠  [{p_id}] {name:<22} | Estoque atual: {stock}")


def general_summary(conn: sqlite3.Connection):
    print("\n======= Resumo Geral =======")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM products;")
    total_products = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM sales;")
    total_sales = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(total_price), 0.0) FROM sales;")
    total_revenue = cursor.fetchone()[0]

    critical_list = ReportService.get_critical_stock_products(cursor, min_threshold=15)
    total_critical = len(critical_list)

    print(f"  Produtos cadastrados : {total_products}")
    print(f"  Vendas realizadas     : {total_sales}")
    print(f"  Receita total        : R$ {total_revenue:.2f}")
    print(f"  Produtos c/ estoque crítico: {total_critical}")
    print("=============================")
