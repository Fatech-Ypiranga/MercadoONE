import sqlite3
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, IntPrompt
from cli.ui import console, pause_and_clear
from repositories.product_repository import ProductRepository
from repositories.stock_repository import StockRepository
from services.stock_service import StockService

BG = "app.borda"
PRIMARY = "app.titulo"
SUCCESS = "sucesso"
WARNING = "aviso"
ERROR = "erro"
SECONDARY = "app.texto"


def stock_menu(conn: sqlite3.Connection):
    while True:
        menu_text = Text()
        menu_text.append("1. 📦 Ver estoque atual\n", style=SECONDARY)
        menu_text.append("2. ➕ Registrar entrada\n", style=SECONDARY)
        menu_text.append("3. ➖ Registrar saída\n", style=SECONDARY)
        menu_text.append("4. 📜 Ver histórico\n", style=SECONDARY)
        menu_text.append("0. ↩️ Voltar\n", style=ERROR)

        console.print(
            Panel(
                menu_text,
                title="[app.titulo]Menu de Estoque[/app.titulo]",
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
            console.print(f"[{WARNING}]Opção inválida.[/{WARNING}]")
            pause_and_clear()


def show_stock(conn: sqlite3.Connection):
    console.print(Panel.fit(Text("Estoque Atual", style=PRIMARY), border_style=BG))
    cursor = conn.cursor()

    products = ProductRepository.find_all(cursor)

    if not products:
        console.print(f"[{WARNING}]Nenhum produto cadastrado.[/{WARNING}]")
        pause_and_clear()
        return

    stock_table = Table(title="Estoque", border_style=BG)
    stock_table.add_column("ID", style=PRIMARY)
    stock_table.add_column("Produto", style=SUCCESS)
    stock_table.add_column("Qtd", justify="right", style=WARNING)
    stock_table.add_column("Status", style=SUCCESS)

    for product in products:
        product_id = product[0]
        product_name = product[1]
        stock = StockRepository.get_current_stock(cursor, product_id)
        status = (f"[{WARNING}]⚠ BAIXO[/{WARNING}]" if stock < 15 else f"[{SUCCESS}]OK[/{SUCCESS}]")
        stock_table.add_row(str(product_id), product_name, str(stock), status)

    console.print(stock_table)
    pause_and_clear()


def register_movement(conn: sqlite3.Connection, movement_type: str):
    cursor = conn.cursor()
    show_stock(conn)

    try:
        product_id = IntPrompt.ask("ID do produto", default="0", show_default=False)
        quantity = IntPrompt.ask("Quantidade", default="1", show_default=False)
    except ValueError:
        console.print(f"[{ERROR}]Entrada inválida.[/{ERROR}]")
        pause_and_clear()
        return

    product = ProductRepository.find_by_id(cursor, product_id)

    if not product:
        console.print(f"[{ERROR}]Produto não encontrado.[/{ERROR}]")
        pause_and_clear()
        return

    if movement_type == "OUT":
        current_stock = StockRepository.get_current_stock(cursor, product_id)
        if current_stock < quantity:
            console.print(f"[{ERROR}]Estoque insuficiente. Disponível: {current_stock}[/{ERROR}]")
            pause_and_clear()
            return

    try:
        StockService.register_movement(conn, product_id, quantity, movement_type)
        new_stock = StockRepository.get_current_stock(cursor, product_id)
        movement_desc = "ENTRADA" if movement_type == "IN" else "SAÍDA"
        console.print(
            f"[{SUCCESS}]✓ Movimentação ({movement_desc}) registrada! Estoque atual de '{product[1]}': {new_stock}[/{SUCCESS}]"
        )
    except Exception as e:
        conn.rollback()
        console.print(f"[{ERROR}]❌ Erro ao registrar movimentação: {e}[/{ERROR}]")
        pause_and_clear()


def show_movements(conn: sqlite3.Connection):
    console.print(Panel.fit(Text("Histórico de Movimentações", style=PRIMARY), border_style=BG))
    cursor = conn.cursor()
    products = ProductRepository.find_all(cursor)

    if not products:
        console.print(f"[{WARNING}]Nenhum produto cadastrado.[/{WARNING}]")
        pause_and_clear()
        return

    movements_table = Table(title="Status atual do estoque", border_style=BG)
    movements_table.add_column("Produto", style=SUCCESS)
    movements_table.add_column("Estoque", justify="right", style=WARNING)

    movements_exist = False
    for product in products:
        product_id = product[0]
        product_name = product[1]
        stock = StockRepository.get_current_stock(cursor, product_id)

        if stock != 0:
            movements_exist = True
            movements_table.add_row(product_name, str(stock))

    if not movements_exist:
        console.print(f"[{SECONDARY}]Nenhuma movimentação registrada. O schema atual mantém o estoque diretamente na tabela produtos.[/{SECONDARY}]")
        pause_and_clear()
        return

    console.print(movements_table)
    pause_and_clear()
