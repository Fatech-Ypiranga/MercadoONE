import sqlite3
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt
from cli.ui import console, pause_and_clear
from services.report_service import ReportService

BG = "app.borda"
PRIMARY = "app.titulo"
SUCCESS = "sucesso"
WARNING = "aviso"
ERROR = "erro"
SECONDARY = "app.texto"


def report_menu(conn: sqlite3.Connection):
    while True:
        menu_text = Text()
        menu_text.append("1. 📈 Top 5 produtos mais vendidos\n", style=SECONDARY)
        menu_text.append("2. 💰 Ticket médio por venda\n", style=SECONDARY)
        menu_text.append("3. ⚠️ Estoque crítico\n", style=SECONDARY)
        menu_text.append("4. 🧾 Resumo geral\n", style=SECONDARY)
        menu_text.append("0. ↩️ Voltar\n", style=ERROR)

        console.print(
            Panel(
                menu_text,
                title="[app.titulo]Menu de Relatórios[/app.titulo]",
                border_style=BG,
                expand=False,
            )
        )

        option = Prompt.ask(
            "Escolha uma opção",
            choices=["1", "2", "3", "4", "0"],
            default="0",
        )

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
            console.print(f"[{WARNING}]Opção inválida.[/{WARNING}]")
            pause_and_clear()


def top_products(conn: sqlite3.Connection):
    console.print(Panel.fit(Text("Top 5 Produtos Mais Vendidos", style=PRIMARY), border_style=BG))
    cursor = conn.cursor()

    ranking = ReportService.get_top_selling_products(cursor, limit=5)

    if not ranking:
        console.print(f"[{WARNING}]Nenhuma venda registrada ainda.[/{WARNING}]")
        pause_and_clear()
        return

    ranking_table = Table(title="Ranking", border_style=BG)
    ranking_table.add_column("#", style=PRIMARY)
    ranking_table.add_column("Produto", style=SUCCESS)
    ranking_table.add_column("Unidades", justify="right", style=WARNING)

    for i, (p_id, name, qty) in enumerate(ranking, start=1):
        ranking_table.add_row(str(i), f"[{p_id}] {name}", str(qty))

    console.print(ranking_table)
    pause_and_clear()


def average_ticket(conn: sqlite3.Connection):
    console.print(Panel.fit(Text("Ticket Médio por Venda", style=PRIMARY), border_style=BG))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM vendas;")
    total_sales = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(valor_total), 0.0) FROM vendas;")
    total_revenue = cursor.fetchone()[0]
    avg = ReportService.get_average_ticket(cursor)

    summary_table = Table(show_header=False, border_style=BG)
    summary_table.add_column("Descrição", style=SECONDARY)
    summary_table.add_column("Valor", style=SUCCESS)
    summary_table.add_row("Vendas realizadas", str(total_sales))
    summary_table.add_row("Receita total", f"R$ {total_revenue:.2f}")
    summary_table.add_row("Ticket médio", f"R$ {avg:.2f}")
    console.print(summary_table)
    pause_and_clear()


def critical_stock(conn: sqlite3.Connection):
    MIN_STOCK = 15
    console.print(Panel.fit(Text(f"Estoque Crítico (abaixo de {MIN_STOCK})", style=WARNING), border_style=BG))
    cursor = conn.cursor()

    critical = ReportService.get_critical_stock_products(cursor, min_threshold=MIN_STOCK)

    if not critical:
        console.print(f"[{SUCCESS}]Nenhum produto em situação crítica.[/{SUCCESS}]")
        pause_and_clear()
        return

    critical_table = Table(title="Produtos em risco", border_style=BG)
    critical_table.add_column("ID", style=PRIMARY)
    critical_table.add_column("Produto", style=WARNING)
    critical_table.add_column("Estoque", justify="right", style=ERROR)

    for p_id, name, stock in critical:
        critical_table.add_row(str(p_id), name, str(stock))

    console.print(critical_table)
    pause_and_clear()


def general_summary(conn: sqlite3.Connection):
    console.print(Panel.fit(Text("Resumo Geral", style=PRIMARY), border_style=BG))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM produtos;")
    total_products = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM vendas;")
    total_sales = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(valor_total), 0.0) FROM vendas;")
    total_revenue = cursor.fetchone()[0]

    critical_list = ReportService.get_critical_stock_products(cursor, min_threshold=15)
    total_critical = len(critical_list)

    summary_table = Table(show_header=False, border_style=BG)
    summary_table.add_column("Descrição", style=SECONDARY)
    summary_table.add_column("Valor", style=SUCCESS)
    summary_table.add_row("Produtos cadastrados", str(total_products))
    summary_table.add_row("Vendas realizadas", str(total_sales))
    summary_table.add_row("Receita total", f"R$ {total_revenue:.2f}")
    summary_table.add_row("Produtos em estoque crítico", str(total_critical))
    console.print(summary_table)
    pause_and_clear()
