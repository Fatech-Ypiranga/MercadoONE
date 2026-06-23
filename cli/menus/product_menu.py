import sqlite3
from repositories.product_repository import ProductRepository
from services.product_service import ProductService
from services.exceptions import BusinessRuleException 

def product_menu(conn: sqlite3.Connection):
    while True:
        print("\n------ Produtos ------")
        print("1. Listar produtos")
        print("2. Cadastrar produto")
        print("0. Voltar")
        print("----------------------")

        option = input("Escolha uma opção: ").strip()

        if option == "1":
            list_products(conn)
        elif option == "2":
            create_product(conn)
        elif option == "0":
            break
        else:
            print("Opção inválida.")


def list_products(conn: sqlite3.Connection):
    print("\n--- Lista de Produtos ---")

    cursor = conn.cursor()
    products = ProductRepository.find_all(cursor)
    
    if not products:
        print("Nenhum produto cadastrado.")
        return
# testar pra ver se deu certo, se nao trocar
    for p in products:
        print(f"[{p['id']}] {p['name']} | {p['category']} | R$ {p['price']:.2f} | Estoque: {p['stock']}")


def create_product(conn: sqlite3.Connection):
    print("\n--- Cadastrar Produto ---")
    
    name = input("Nome: ").strip()
    description = input("Descrição (opcional): ").strip()
    
    try:
        price = float(input("Preço: R$ "))
        category_id = int(input("ID da Categoria existente: "))
    except ValueError:
        print("Erro: Preço e ID da Categoria precisam ser valores numéricos válidos.")
        return

    try:
        
        new_id = ProductService.create_product(
            conn=conn, 
            name=name, 
            description=description, 
            price=price, 
            category_id=category_id
        )
        print(f"\nProduto '{name}' cadastrado com sucesso de forma segura! (ID Gerado: {new_id})")
        
    except BusinessRuleException as e:
        # Captura centralizada de qualquer erro lançado pelo service (ex: Categoria inexistente, Preço inválido)
        print(f"\n❌ Erro de Negócio: {e}")