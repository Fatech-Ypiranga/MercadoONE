# Dados mockados — serão substituídos pelas chamadas ao service depois
MOCK_PRODUCTS = [
    {"id": 1, "name": "Notebook Gamer", "category": "Eletrônicos", "price": 4500.00, "stock": 10},
    {"id": 2, "name": "Mouse Sem Fio",  "category": "Periféricos",  "price": 120.00,  "stock": 35},
    {"id": 3, "name": "Teclado Mecânico","category": "Periféricos", "price": 280.00,  "stock": 20},
]


def product_menu():
    while True:
        print("\n------ Produtos ------")
        print("1. Listar produtos")
        print("2. Cadastrar produto")
        print("0. Voltar")
        print("----------------------")

        option = input("Escolha uma opção: ").strip()

        if option == "1":
            list_products()
        elif option == "2":
            create_product()
        elif option == "0":
            break
        else:
            print("Opção inválida.")


def list_products():
    print("\n--- Lista de Produtos ---")
    if not MOCK_PRODUCTS:
        print("Nenhum produto cadastrado.")
        return

    for p in MOCK_PRODUCTS:
        print(f"[{p['id']}] {p['name']} | {p['category']} | R$ {p['price']:.2f} | Estoque: {p['stock']}")


def create_product():
    print("\n--- Cadastrar Produto ---")
    name     = input("Nome: ").strip()
    category = input("Categoria: ").strip()
    price    = float(input("Preço: R$ "))
    stock    = int(input("Estoque inicial: "))

    new_id = max(p["id"] for p in MOCK_PRODUCTS) + 1 if MOCK_PRODUCTS else 1
    new_product = {"id": new_id, "name": name, "category": category, "price": price, "stock": stock}

    MOCK_PRODUCTS.append(new_product)
    print(f"\nProduto '{name}' cadastrado com sucesso! (ID: {new_id})")
