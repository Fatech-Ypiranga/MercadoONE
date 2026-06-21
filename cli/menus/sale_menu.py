from cli.menus.product_menu import MOCK_PRODUCTS

MOCK_CUSTOMERS = [
    {"id": 1, "name": "Ana Silva",   "email": "ana@email.com"},
    {"id": 2, "name": "Bruno Costa", "email": "bruno@email.com"},
]

MOCK_SALES = []


def sale_menu():
    while True:
        print("\n------ Vendas ------")
        print("1. Nova venda")
        print("2. Listar vendas")
        print("3. Cadastrar cliente")
        print("0. Voltar")
        print("--------------------")

        option = input("Escolha uma opção: ").strip()

        if option == "1":
            create_sale()
        elif option == "2":
            list_sales()
        elif option == "3":
            create_customer()
        elif option == "0":
            break
        else:
            print("Opção inválida.")


def create_sale():
    print("\n--- Nova Venda ---")

    # Selecionar cliente
    print("\nClientes disponíveis:")
    for c in MOCK_CUSTOMERS:
        print(f"  [{c['id']}] {c['name']}")

    try:
        customer_id = int(input("ID do cliente (0 para venda sem cliente): "))
    except ValueError:
        print("Entrada inválida.")
        return

    customer = next((c for c in MOCK_CUSTOMERS if c["id"] == customer_id), None)
    customer_name = customer["name"] if customer else "Consumidor Final"

    # Montar carrinho
    items = []
    while True:
        print("\n--- Produtos disponíveis ---")
        for p in MOCK_PRODUCTS:
            print(f"  [{p['id']}] {p['name']:<20} | R$ {p['price']:.2f} | Estoque: {p['stock']}")

        product_input = input("\nID do produto (0 para finalizar): ").strip()
        if product_input == "0":
            break

        try:
            product_id = int(product_input)
            quantity   = int(input("Quantidade: "))
        except ValueError:
            print("Entrada inválida.")
            continue

        product = next((p for p in MOCK_PRODUCTS if p["id"] == product_id), None)
        if not product:
            print("Produto não encontrado.")
            continue

        if product["stock"] < quantity:
            print(f"Estoque insuficiente. Disponível: {product['stock']}")
            continue

        # Desconta estoque imediatamente (comportamento otimista)
        product["stock"] -= quantity

        items.append({
            "product_id":   product["id"],
            "product_name": product["name"],
            "quantity":     quantity,
            "unit_price":   product["price"],
            "subtotal":     product["price"] * quantity,
        })
        print(f"  ✓ {product['name']} x{quantity} adicionado.")

    if not items:
        print("Nenhum item adicionado. Venda cancelada.")
        return

    total = sum(i["subtotal"] for i in items)
    sale_id = len(MOCK_SALES) + 1

    sale = {
        "id":            sale_id,
        "customer_name": customer_name,
        "items":         items,
        "total":         total,
    }
    MOCK_SALES.append(sale)

    # Recibo
    print(f"\n{'='*35}")
    print(f"  VENDA #{sale_id} — {customer_name}")
    print(f"{'='*35}")
    for item in items:
        print(f"  {item['product_name']:<20} x{item['quantity']} = R$ {item['subtotal']:.2f}")
    print(f"{'='*35}")
    print(f"  TOTAL: R$ {total:.2f}")
    print(f"{'='*35}")


def list_sales():
    print("\n--- Vendas Realizadas ---")
    if not MOCK_SALES:
        print("Nenhuma venda registrada.")
        return

    for s in MOCK_SALES:
        print(f"Venda #{s['id']} | {s['customer_name']:<20} | {len(s['items'])} item(s) | Total: R$ {s['total']:.2f}")


def create_customer():
    print("\n--- Cadastrar Cliente ---")
    name  = input("Nome: ").strip()
    email = input("E-mail: ").strip()

    new_id = max(c["id"] for c in MOCK_CUSTOMERS) + 1 if MOCK_CUSTOMERS else 1
    MOCK_CUSTOMERS.append({"id": new_id, "name": name, "email": email})
    print(f"Cliente '{name}' cadastrado! (ID: {new_id})")
