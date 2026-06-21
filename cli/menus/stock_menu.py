from cli.menus.product_menu import MOCK_PRODUCTS

# Histórico de movimentações mockado
MOCK_MOVEMENTS = []


def stock_menu():
    while True:
        print("\n------ Estoque ------")
        print("1. Ver estoque atual")
        print("2. Registrar entrada")
        print("3. Registrar saída")
        print("4. Ver histórico de movimentações")
        print("0. Voltar")
        print("---------------------")

        option = input("Escolha uma opção: ").strip()

        if option == "1":
            show_stock()
        elif option == "2":
            register_movement("entrada")
        elif option == "3":
            register_movement("saida")
        elif option == "4":
            show_movements()
        elif option == "0":
            break
        else:
            print("Opção inválida.")


def show_stock():
    print("\n--- Estoque Atual ---")
    for p in MOCK_PRODUCTS:
        status = "⚠ BAIXO" if p["stock"] < 15 else "OK"
        print(f"[{p['id']}] {p['name']:<20} | Qtd: {p['stock']:>4} | {status}")


def register_movement(movement_type):
    show_stock()
    try:
        product_id = int(input("\nID do produto: "))
        quantity   = int(input("Quantidade: "))
        reason     = input("Motivo (ex: compra, venda, ajuste): ").strip()
    except ValueError:
        print("Entrada inválida.")
        return

    product = next((p for p in MOCK_PRODUCTS if p["id"] == product_id), None)

    if not product:
        print("Produto não encontrado.")
        return

    if movement_type == "saida" and product["stock"] < quantity:
        print(f"Estoque insuficiente. Disponível: {product['stock']}")
        return

    if movement_type == "entrada":
        product["stock"] += quantity
    else:
        product["stock"] -= quantity

    movement = {
        "product_id":   product_id,
        "product_name": product["name"],
        "type":         movement_type,
        "quantity":     quantity,
        "reason":       reason,
    }
    MOCK_MOVEMENTS.append(movement)
    print(f"\nMovimentação registrada! Estoque atual de '{product['name']}': {product['stock']}")


def show_movements():
    print("\n--- Histórico de Movimentações ---")
    if not MOCK_MOVEMENTS:
        print("Nenhuma movimentação registrada.")
        return

    for m in MOCK_MOVEMENTS:
        arrow = "▲ ENTRADA" if m["type"] == "entrada" else "▼ SAÍDA"
        print(f"{arrow} | {m['product_name']:<20} | Qtd: {m['quantity']:>4} | Motivo: {m['reason']}")
