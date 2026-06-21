from cli.menus.product_menu import MOCK_PRODUCTS
from cli.menus.sale_menu import MOCK_SALES


def report_menu():
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
            top_products()
        elif option == "2":
            average_ticket()
        elif option == "3":
            critical_stock()
        elif option == "4":
            general_summary()
        elif option == "0":
            break
        else:
            print("Opção inválida.")


def top_products():
    print("\n--- Top 5 Produtos Mais Vendidos ---")
    if not MOCK_SALES:
        print("Nenhuma venda registrada ainda.")
        return

    # Agrupa quantidade vendida por produto usando dicionário
    sales_count = {}
    for sale in MOCK_SALES:
        for item in sale["items"]:
            name = item["product_name"]
            sales_count[name] = sales_count.get(name, 0) + item["quantity"]

    # Ordena do maior para o menor e pega os 5 primeiros
    ranking = sorted(sales_count.items(), key=lambda x: x[1], reverse=True)[:5]

    for i, (name, qty) in enumerate(ranking, start=1):
        print(f"  {i}º {name:<22} — {qty} unidades vendidas")


def average_ticket():
    print("\n--- Ticket Médio por Venda ---")
    if not MOCK_SALES:
        print("Nenhuma venda registrada ainda.")
        return

    total_revenue = sum(s["total"] for s in MOCK_SALES)
    avg = total_revenue / len(MOCK_SALES)

    print(f"  Vendas realizadas : {len(MOCK_SALES)}")
    print(f"  Receita total     : R$ {total_revenue:.2f}")
    print(f"  Ticket médio      : R$ {avg:.2f}")


def critical_stock():
    MIN_STOCK = 15
    print(f"\n--- Estoque Crítico (abaixo de {MIN_STOCK} unidades) ---")

    critical = [p for p in MOCK_PRODUCTS if p["stock"] < MIN_STOCK]

    if not critical:
        print("  Nenhum produto em situação crítica.")
        return

    for p in critical:
        print(f"  ⚠  {p['name']:<22} | Estoque atual: {p['stock']}")


def general_summary():
    print("\n======= Resumo Geral =======")
    print(f"  Produtos cadastrados : {len(MOCK_PRODUCTS)}")
    print(f"  Vendas realizadas    : {len(MOCK_SALES)}")

    total_revenue = sum(s["total"] for s in MOCK_SALES) if MOCK_SALES else 0
    print(f"  Receita total        : R$ {total_revenue:.2f}")

    critical = [p for p in MOCK_PRODUCTS if p["stock"] < 15]
    print(f"  Produtos c/ estoque crítico: {len(critical)}")
    print("=============================")
