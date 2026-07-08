from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from cli.ui import console
from cli.menus.product_menu import product_menu
from cli.menus.sale_menu import sale_menu
from cli.menus.stock_menu import stock_menu
from cli.menus.report_menu import report_menu
from database.connection import DatabaseConnection

DatabaseConnection.run_migrations()

def main_menu():
    while True:
        menu_text = Text()
        menu_text.append("1. 📦 Produtos\n", style="menu.texto")
        menu_text.append("2. 🛒 Vendas\n", style="menu.texto")
        menu_text.append("3. 📦 Estoque\n", style="menu.texto")
        menu_text.append("4. 📊 Relatórios\n", style="menu.texto")
        menu_text.append("0. 🚪 Sair\n", style="erro")

        menu_panel = Panel(
            menu_text,
            title="[app.titulo]Menu Principal[/app.titulo]",
            border_style="app.borda",
            expand=False
        )

        console.print(menu_panel)

        option = Prompt.ask(
            "Escolha uma opção",
            choices=["1", "2", "3", "4", "0"],
            default="0"
        )

        if option == "0":
            console.print("\n[aviso] Saindo do sistema. Até logo![/aviso]")
            break

        with DatabaseConnection.get_connection() as conn:
            if option == "1":
                product_menu(conn)
            elif option == "2":
                sale_menu(conn)
            elif option == "3":
                stock_menu(conn)
            elif option == "4":
                report_menu(conn)
            else:
                console.print("[erro]Opção inválida. Tente novamente.[/erro]")

if __name__ == "__main__":
    DatabaseConnection.run_migrations()  # Garante que as migrações sejam aplicadas antes de iniciar o menu
    main_menu()
