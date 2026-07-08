import sqlite3
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, IntPrompt
from cli.ui import console, pause_and_clear
from repositories.customer_repository import CustomerRepository
from repositories.product_repository import ProductRepository
from repositories.sale_repository import SaleRepository
from repositories.stock_repository import StockRepository
from services.sale_service import SaleService
from services.exceptions import ValidationError, ResourceNotFoundException, InsufficientStockException, BusinessRuleException

BG = "app.borda"
PRIMARY = "app.titulo"
SUCCESS = "sucesso"
WARNING = "aviso"
ERROR = "erro"
SECONDARY = "app.texto"


def sale_menu(conn: sqlite3.Connection):
    while True:
        menu_text = Text()
        menu_text.append("1. 🛒 Nova venda\n", style=SECONDARY)
        menu_text.append("2. 📋 Listar vendas\n", style=SECONDARY)
        menu_text.append("3. 👤 Cadastrar cliente\n", style=SECONDARY)
        menu_text.append("0. ↩️ Voltar\n", style=ERROR)

        console.print(
            Panel(
                menu_text,
                title="[app.titulo]Menu de Vendas[/app.titulo]",
                border_style=BG,
                expand=False,
            )
        )

        option = Prompt.ask(
            "Escolha uma opção",
            choices=["1", "2", "3", "0"],
            default="0",
        )

        if option == "1":
            create_sale(conn)
        elif option == "2":
            list_sales(conn)
        elif option == "3":
            create_customer(conn)
        elif option == "0":
            break
        else:
            console.print(f"[{WARNING}]Opção inválida.[/{WARNING}]")
            pause_and_clear()


def create_sale(conn: sqlite3.Connection):
    console.print(Panel.fit(Text("Nova Venda", style=PRIMARY), border_style=BG))
    cursor = conn.cursor()

    console.print(f"[{SECONDARY}]Clientes disponíveis:[/{SECONDARY}]")
    customers = CustomerRepository.find_all(cursor)

    if not customers:
        console.print(f"[{WARNING}]Nenhum cliente disponível. Cadastre um cliente primeiro.[/{WARNING}]")
        pause_and_clear()
        return

    customer_table = Table(show_header=False, box=None)
    customer_table.add_column("id", style=PRIMARY)
    customer_table.add_column("nome", style=SUCCESS)
    for customer in customers:
        customer_table.add_row(str(customer[0]), customer[1])
    console.print(customer_table)

    try:
        customer_id = IntPrompt.ask("ID do cliente (0 para venda sem cliente)", default="0", show_default=False)
    except ValueError:
        console.print(f"[{ERROR}]Entrada inválida.[/{ERROR}]")
        pause_and_clear()
        return

    if customer_id == 0:
        customer_id = None
    else:
        customer = CustomerRepository.find_by_id(cursor, customer_id)
        if not customer:
            console.print(f"[{ERROR}]Cliente não encontrado.[/{ERROR}]")
            pause_and_clear()
            return

    items = []
    while True:
        console.print(f"[{SECONDARY}]Produtos disponíveis:[/{SECONDARY}]")
        products = ProductRepository.find_all(cursor)

        if not products:
            console.print(f"[{WARNING}]Nenhum produto disponível.[/{WARNING}]")
            pause_and_clear()
            break

        product_table = Table(show_header=True, box=None)
        product_table.add_column("ID", style=PRIMARY)
        product_table.add_column("Produto", style=SUCCESS)
        product_table.add_column("Preço", style=SUCCESS)
        product_table.add_column("Estoque", style=WARNING)
        for product in products:
            stock = StockRepository.get_current_stock(cursor, product[0])
            product_table.add_row(str(product[0]), product[1], f"R$ {product[3]:.2f}", str(stock))
        console.print(product_table)

        product_input = Prompt.ask("ID do produto (0 para finalizar)", default="0", show_default=False)
        if product_input == "0":
            break

        try:
            product_id = int(product_input)
            quantity = IntPrompt.ask("Quantidade", default="1", show_default=False)
        except ValueError:
            console.print(f"[{ERROR}]Entrada inválida.[/{ERROR}]")
            continue

        product = ProductRepository.find_by_id(cursor, product_id)
        if not product:
            console.print(f"[{ERROR}]Produto não encontrado.[/{ERROR}]")
            continue

        stock = StockRepository.get_current_stock(cursor, product_id)
        if stock < quantity:
            console.print(f"[{ERROR}]Estoque insuficiente. Disponível: {stock}[/{ERROR}]")
            continue

        items.append({"product_id": product_id, "quantity": quantity})
        console.print(f"[{SUCCESS}]✓ {product[1]} x{quantity} adicionado.[/{SUCCESS}]")

    if not items:
        console.print(f"[{WARNING}]Nenhum item adicionado. Venda cancelada.[/{WARNING}]")
        pause_and_clear()
        return

    try:
        sale_id = SaleService.process_sale(conn, customer_id, items)
        cursor = conn.cursor()
        sale = SaleRepository.find_by_id(cursor, sale_id)
        sale_items = SaleRepository.find_items_by_sale(cursor, sale_id)

        if customer_id:
            customer = CustomerRepository.find_by_id(cursor, customer_id)
            customer_name = customer[1] if customer else "Desconhecido"
        else:
            customer_name = "Consumidor Final"

        receipt = Table(title=f"Venda #{sale_id} — {customer_name}", header_style=PRIMARY, border_style=BG)
        receipt.add_column("Produto", style=SUCCESS)
        receipt.add_column("Qtd", justify="right", style=WARNING)
        receipt.add_column("Subtotal", justify="right", style=SUCCESS)

        for item in sale_items:
            product = ProductRepository.find_by_id(cursor, item[1])
            subtotal = item[2] * item[3]
            receipt.add_row(product[1], str(item[2]), f"R$ {subtotal:.2f}")

        receipt.add_row("[bold]TOTAL[/bold]", "", f"[bold]{sale[4]:.2f}[/bold]")
        console.print(receipt)

    except (ValidationError, ResourceNotFoundException, InsufficientStockException, BusinessRuleException) as e:
        console.print(f"[{ERROR}]❌ Erro na venda: {e}[/{ERROR}]")
        pause_and_clear()


def list_sales(conn: sqlite3.Connection):
    console.print(Panel.fit(Text("Vendas Realizadas", style=PRIMARY), border_style=BG))
    cursor = conn.cursor()
    sales = SaleRepository.find_all(cursor)

    if not sales:
        console.print(f"[{WARNING}]Nenhuma venda registrada.[/{WARNING}]")
        pause_and_clear()
        return

    sales_table = Table(title="Histórico de Vendas", border_style=BG)
    sales_table.add_column("ID", style=PRIMARY)
    sales_table.add_column("Cliente", style=SUCCESS)
    sales_table.add_column("Itens", justify="right", style=WARNING)
    sales_table.add_column("Total", justify="right", style=SUCCESS)

    for sale in sales:
        sale_id = sale[0]
        customer_id = sale[1]
        total_price = sale[4]

        if customer_id:
            customer = CustomerRepository.find_by_id(cursor, customer_id)
            customer_name = customer[1] if customer else "Desconhecido"
        else:
            customer_name = "Consumidor Final"

        items = SaleRepository.find_items_by_sale(cursor, sale_id)
        sales_table.add_row(str(sale_id), customer_name, str(len(items)), f"R$ {total_price:.2f}")

    console.print(sales_table)
    pause_and_clear()


def create_customer(conn: sqlite3.Connection):
    console.print(Panel.fit(Text("Cadastrar Cliente", style=PRIMARY), border_style=BG))
    cursor = conn.cursor()

    name = Prompt.ask("Nome", default="", show_default=False)
    cpf = Prompt.ask("CPF", default="", show_default=False)
    email = Prompt.ask("E-mail", default="", show_default=False)
    phone = Prompt.ask("Telefone (opcional)", default="", show_default=False)

    try:
        new_id = CustomerRepository.create(cursor, name, cpf, email, phone)
        conn.commit()
        console.print(f"[{SUCCESS}]Cliente '{name}' cadastrado! (ID: {new_id})[/{SUCCESS}]")
    except Exception as e:
        conn.rollback()
        console.print(f"[{ERROR}]❌ Erro ao cadastrar cliente: {e}[/{ERROR}]")
        pause_and_clear()
