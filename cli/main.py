from cli.menus.product_menu import product_menu
from cli.menus.sale_menu import sale_menu
from cli.menus.stock_menu import stock_menu
from cli.menus.report_menu import report_menu
from database.connection import DatabaseConnection

DatabaseConnection.run_migrations()

def main_menu():
    with DatabaseConnection.get_connection() as conn:
        while True:
            print("\n========== PyERP ==========")
            print("1. Produtos")
            print("2. Vendas")
            print("3. Estoque")
            print("4. Relatórios")
            print("0. Sair")
            print("===========================")

            option = input("Escolha uma opção: ").strip()

            if option == "1":
                product_menu(conn)
            elif option == "2":
                sale_menu(conn)
            elif option == "3":
                stock_menu(conn)
            elif option == "4":
                report_menu(conn)
            elif option == "0": 
                print("Encerrando o sistema. Até logo!")
                break
            else:
                print("Opção inválida. Tente novamente.")


if __name__ == "__main__":
    main_menu()
