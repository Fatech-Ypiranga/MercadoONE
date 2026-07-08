import sqlite3
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, FloatPrompt, IntPrompt
from rich.table import Table
from cli.ui import console, pause_and_clear
from repositories.product_repository import ProductRepository
from repositories.category_repository import CategoryRepository
from services.product_service import ProductService
from services.exceptions import BusinessRuleException 

BG = "app.borda"
PRIMARY = "app.titulo"
SUCCESS = "sucesso"
WARNING = "aviso"
ERROR = "erro"
SECONDARY = "app.texto"

def product_menu(conn: sqlite3.Connection):
    while True:
        menu_text = Text()
        menu_text.append("1. 📋 Listar Produtos\n", style="menu.texto")
        menu_text.append("2. 📦 Cadastrar Produto\n", style="menu.texto")
        menu_text.append("3. 🗂️ Gerenciar Categorias\n", style="menu.texto")
        menu_text.append("0. 🚪 Voltar\n", style="erro")

        menu_panel = Panel(
            menu_text,
            title="[app.titulo]Menu de Produtos[/app.titulo]",
            border_style="app.borda",
            expand=False
        )

        console.print(menu_panel)

        option = Prompt.ask(
            "Escolha uma opção",
            choices=["1", "2", "3", "0"],
            default="0"
        )

        if option == "1":
            list_products(conn)
        elif option == "2":
            create_product(conn)
        elif option == "3":
            category_menu(conn)
        elif option == "0":
            break
        else:
            console.print("[app.texto]Opção inválida.[/app.texto]")
            pause_and_clear()

def list_products(conn: sqlite3.Connection):
    table = Table(title="Lista de Produtos", show_lines=True)
    table.add_column("ID", justify="center", style="app.titulo", no_wrap=True)
    table.add_column("Nome", justify="right", style="sucesso")
    table.add_column("Categoria", justify="right", style="app.texto")
    table.add_column("Preço", justify="right", style="sucesso")
    table.add_column("Estoque", justify="right", style="aviso")

    cursor = conn.cursor()
    products = ProductRepository.find_all(cursor)
    
    if not products:
        console.print("[dimmed]Nenhum produto cadastrado.[/dimmed]")
        pause_and_clear()
        return

    for p in products:
        category = CategoryRepository.find_by_id(cursor, p[4]) if p[4] is not None else None
        category_name = category[1] if category else "Sem categoria"
        table.add_row(str(p[0]), p[1], category_name, f"R$ {p[3]:.2f}", str(p[5]))
    console.print(table)
    pause_and_clear("Pressione Enter para voltar ao menu de produtos")


def create_product(conn: sqlite3.Connection):
    console.print("\n[app.titulo]--- Cadastrar Produto ---[/app.titulo]")
    
    name = Prompt.ask("Nome do Produto: ", default="", show_default=False)
    description = Prompt.ask("Descrição (opcional): ", default="", show_default=False)

    try:
        price = FloatPrompt.ask("Preço: ", default="0.00", show_default=False)
        category_id = IntPrompt.ask("ID da Categoria existente: ", default="0", show_default=False)
    except ValueError:
        console.print("[erro]❌ Erro: Preço e ID da Categoria precisam ser valores numéricos válidos.[/erro]")
        pause_and_clear()
        return

    try:
        
        new_id = ProductService.create_product(
            conn=conn, 
            name=name, 
            description=description, 
            price=price, 
            category_id=category_id
        )
        
        console.print(f"\n[sucesso]✓[/sucesso] Produto '{name}' cadastrado com sucesso! [dimmed]ID: {new_id}[/dimmed]")
        pause_and_clear()
    except BusinessRuleException as e:
        console.print(f"\n[erro]❌ Erro de Negócio:[/erro] {e}")
        pause_and_clear()


def category_menu(conn: sqlite3.Connection):
    while True:
        menu_text = Text()
        menu_text.append("1. 📋 Listar categorias\n", style="menu.texto")
        menu_text.append("2. ➕ Criar categoria\n", style="menu.texto")
        menu_text.append("3. ✏️ Editar categoria\n", style="menu.texto")
        menu_text.append("4. 🗑️ Excluir categoria\n", style="menu.texto")
        menu_text.append("0. ↩️ Voltar\n", style="erro")

        console.print(
            Panel(
                menu_text,
                title="[app.titulo]Menu de Categorias[/app.titulo]",
                border_style="app.borda",
                expand=False,
            )
        )

        option = Prompt.ask(
            "Escolha uma opção",
            choices=["1", "2", "3", "4", "0"],
            default="0",
        )

        if option == "1":
            list_categories(conn)
        elif option == "2":
            create_category(conn)
        elif option == "3":
            update_category(conn)
        elif option == "4":
            delete_category(conn)
        elif option == "0":
            break
        else:
            console.print("[app.texto]Opção inválida.[/app.texto]")
            pause_and_clear()


def list_categories(conn: sqlite3.Connection):
    categories_table = build_categories_table(conn)

    if categories_table is None:
        console.print("[dimmed]Nenhuma categoria cadastrada.[/dimmed]")
        pause_and_clear()
        return

    console.print(categories_table)
    pause_and_clear("Pressione Enter para voltar ao menu de categorias")


def build_categories_table(conn: sqlite3.Connection):
    cursor = conn.cursor()
    categories = CategoryRepository.find_all(cursor)

    if not categories:
        return None

    table = Table(title="Lista de Categorias", show_lines=True)
    table.add_column("ID", justify="center", style="app.titulo", no_wrap=True)
    table.add_column("Nome", style="sucesso")
    table.add_column("Descrição", style="app.texto")

    for category in categories:
        table.add_row(str(category[0]), category[1], category[2] or "")

    return table


def create_category(conn: sqlite3.Connection):
    console.print("\n[app.titulo]--- Criar Categoria ---[/app.titulo]")
    cursor = conn.cursor()

    name = Prompt.ask("Nome da categoria", default="", show_default=False)
    description = Prompt.ask("Descrição (opcional)", default="", show_default=False)

    try:
        category_id = CategoryRepository.create(cursor, name, description)
        conn.commit()
        console.print(f"[sucesso]✓ Categoria '{name}' criada com sucesso![/sucesso] [dimmed]ID: {category_id}[/dimmed]")
    except Exception as e:
        conn.rollback()
        console.print(f"[erro]❌ Erro ao criar categoria:[/erro] {e}")

    pause_and_clear()


def update_category(conn: sqlite3.Connection):
    console.print("\n[app.titulo]--- Editar Categoria ---[/app.titulo]")
    cursor = conn.cursor()
    categories_table = build_categories_table(conn)

    if categories_table is None:
        console.print("[dimmed]Nenhuma categoria cadastrada.[/dimmed]")
        pause_and_clear()
        return

    console.print(categories_table)

    try:
        category_id = IntPrompt.ask("ID da categoria", default="0", show_default=False)
    except ValueError:
        console.print("[erro]ID inválido.[/erro]")
        pause_and_clear()
        return

    category = CategoryRepository.find_by_id(cursor, category_id)
    if not category:
        console.print("[erro]Categoria não encontrada.[/erro]")
        pause_and_clear()
        return

    name = Prompt.ask("Novo nome", default=category[1], show_default=True)
    description = Prompt.ask("Nova descrição", default=category[2] or "", show_default=True)

    try:
        updated = CategoryRepository.update(cursor, category_id, name, description)
        conn.commit()
        if updated:
            console.print("[sucesso]✓ Categoria atualizada com sucesso.[/sucesso]")
        else:
            console.print("[aviso]Nenhuma alteração foi aplicada.[/aviso]")
    except Exception as e:
        conn.rollback()
        console.print(f"[erro]❌ Erro ao atualizar categoria:[/erro] {e}")

    pause_and_clear()


def delete_category(conn: sqlite3.Connection):
    console.print("\n[app.titulo]--- Excluir Categoria ---[/app.titulo]")
    cursor = conn.cursor()
    categories_table = build_categories_table(conn)

    if categories_table is None:
        console.print("[dimmed]Nenhuma categoria cadastrada.[/dimmed]")
        pause_and_clear()
        return

    console.print(categories_table)

    try:
        category_id = IntPrompt.ask("ID da categoria", default="0", show_default=False)
    except ValueError:
        console.print("[erro]ID inválido.[/erro]")
        pause_and_clear()
        return

    category = CategoryRepository.find_by_id(cursor, category_id)
    if not category:
        console.print("[erro]Categoria não encontrada.[/erro]")
        pause_and_clear()
        return

    confirm = Prompt.ask(
        f"Confirma a exclusão de '{category[1]}'?",
        choices=["s", "n"],
        default="n",
    )

    if confirm != "s":
        console.print("[aviso]Exclusão cancelada.[/aviso]")
        pause_and_clear()
        return

    try:
        deleted = CategoryRepository.delete(cursor, category_id)
        conn.commit()
        if deleted:
            console.print("[sucesso]✓ Categoria excluída com sucesso.[/sucesso]")
        else:
            console.print("[aviso]Nenhuma categoria foi excluída.[/aviso]")
    except Exception as e:
        conn.rollback()
        console.print(f"[erro]❌ Erro ao excluir categoria:[/erro] {e}")

    pause_and_clear()