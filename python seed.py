
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlmodel import Session

try:
    from database.connection import engine
except ImportError as exc:
    raise ImportError(
        "Não encontrei `engine` em database.connection. Abre esse arquivo e "
        "ajusta o import no topo deste script para o nome real (ex.: "
        "get_engine(), db_engine, etc.)."
    ) from exc

from auth.security import hash_password
from models import (
    Branch,
    Category,
    Company,
    Customer,
    Product,
    PurchaseItem,
    PurchaseOrder,
    Sale,
    SaleItem,
    StockMovement,
    Store,
    Supplier,
    SupplierAddress,
    User,
)
from utils.enums import (
    CustomerType,
    MovementReason,
    MovementType,
    PurchaseStatus,
    StateRegistrationIndicator,
    UserProfile,
)

random.seed(42)  # reprodutível — mesma "aleatoriedade" toda vez que rodar

SALE_STATUS_CONCLUIDA = "Concluida"
SALE_STATUS_CANCELADA = "Cancelada"

PAYMENT_METHODS = ["dinheiro", "cartao_credito", "cartao_debito", "pix"]

PRODUCT_CATALOG = [
    ("Arroz Branco 5kg", "ALI", Decimal("18.50"), Decimal("27.90")),
    ("Feijão Carioca 1kg", "ALI", Decimal("6.20"), Decimal("9.80")),
    ("Óleo de Soja 900ml", "ALI", Decimal("5.10"), Decimal("8.50")),
    ("Açúcar Refinado 1kg", "ALI", Decimal("3.40"), Decimal("5.90")),
    ("Café Torrado 500g", "ALI", Decimal("9.80"), Decimal("15.90")),
    ("Detergente Neutro 500ml", "LIM", Decimal("2.10"), Decimal("3.90")),
    ("Sabão em Pó 1kg", "LIM", Decimal("8.90"), Decimal("14.50")),
    ("Amaciante 2L", "LIM", Decimal("11.20"), Decimal("18.90")),
    ("Papel Higiênico 12un", "LIM", Decimal("14.50"), Decimal("22.90")),
    ("Água Sanitária 1L", "LIM", Decimal("3.20"), Decimal("5.50")),
    ("Refrigerante Cola 2L", "BEB", Decimal("6.50"), Decimal("9.90")),
    ("Suco de Laranja 1L", "BEB", Decimal("5.80"), Decimal("8.90")),
    ("Cerveja Lager 350ml", "BEB", Decimal("2.90"), Decimal("4.90")),
    ("Água Mineral 1,5L", "BEB", Decimal("1.80"), Decimal("3.20")),
    ("Biscoito Recheado 140g", "SNK", Decimal("2.40"), Decimal("4.50")),
]

CATEGORY_NAMES = [
    ("Alimentos", "alimentos"),
    ("Limpeza", "limpeza"),
    ("Bebidas", "bebidas"),
    ("Snacks", "snacks"),
    ("Diversos", "diversos"),
]

CUSTOMER_NAMES = [
    "Maria Silva", "João Santos", "Ana Oliveira", "Carlos Souza",
    "Fernanda Lima", "Pedro Costa", "Juliana Alves", "Rafael Pereira",
]

SUPPLIER_NAMES = [
    ("Distribuidora Central LTDA", "12345678000190"),
    ("Atacadão Boa Vista LTDA", "98765432000110"),
    ("Comercial Nordeste LTDA", "45678912000155"),
]


def _dt_days_ago(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(
        days=days, hours=random.randint(8, 20), minutes=random.randint(0, 59)
    )


def seed() -> None:
    with Session(engine) as session:
        # ---------- Empresa / Filial / Lojas ----------
        company = Company(
            legal_name="PyERP Demo LTDA",
            trade_name="PyERP Demo",
            document="11222333000181",
            is_active=True,
        )
        session.add(company)
        session.flush()

        branch = Branch(name="Matriz", code="MTZ", company_id=company.id, is_active=True)
        session.add(branch)
        session.flush()

        store_centro = Store(
            name="Loja Centro", code="LC01", company_id=company.id,
            branch_id=branch.id, is_active=True,
        )
        store_norte = Store(
            name="Loja Norte", code="LN01", company_id=company.id,
            branch_id=branch.id, is_active=True,
        )
        session.add(store_centro)
        session.add(store_norte)
        session.flush()
        stores = [store_centro, store_norte]

        # ---------- Usuário admin ----------
        admin = User(
            full_name="Administrador Demo",
            cpf="00000000000",
            email="admin@pyerp.local",
            username="admin",
            profile=UserProfile.ADMIN,
            password_hash=hash_password("Admin123!"),
            company_id=company.id,
            default_branch_id=branch.id,
            default_store_id=store_centro.id,
            is_active=True,
        )
        session.add(admin)
        session.flush()

        # ---------- Categorias ----------
        categories = {}
        for name, slug in CATEGORY_NAMES:
            cat = Category(
                name=name, slug=slug, company_id=company.id,
                is_active=True, created_by=admin.id,
            )
            session.add(cat)
            session.flush()
            categories[slug] = cat

        cat_map = {
            "ALI": categories["alimentos"],
            "LIM": categories["limpeza"],
            "BEB": categories["bebidas"],
            "SNK": categories["snacks"],
        }

        # ---------- Fornecedores ----------
        suppliers = []
        for idx, (name, doc) in enumerate(SUPPLIER_NAMES, start=1):
            supplier = Supplier(
                name=name, trade_name=name.split(" LTDA")[0],
                document=doc, company_id=company.id, code=f"F{idx:03d}",
                is_active=True, created_by=admin.id,
            )
            session.add(supplier)
            session.flush()
            address = SupplierAddress(
                supplier_id=supplier.id,
                description="Principal",
                zip_code="01310100",
                street="Av. Paulista",
                number=str(1000 + idx),
                neighborhood="Bela Vista",
                city="São Paulo",
                state="SP",
                ibge_code="3550308",
                created_by=admin.id,
            )
            session.add(address)
            suppliers.append(supplier)
        session.flush()

        # ---------- Produtos + estoque inicial ----------
        products = []
        for idx, (name, cat_code, cost, price) in enumerate(PRODUCT_CATALOG, start=1):
            product = Product(
                name=name,
                sku=f"SKU{idx:04d}",
                barcode=f"789{idx:010d}",
                is_active=True,
                cost_price=cost,
                sale_price=price,
                unit_of_measure="UN",
                category_id=cat_map[cat_code].id,
                company_id=company.id,
                material_code=f"{idx:07d}",
                primary_supplier_id=random.choice(suppliers).id,
                created_by=admin.id,
            )
            session.add(product)
            session.flush()
            products.append(product)

            # Estoque inicial: a maioria confortável, ~1/4 de propósito baixo
            for store in stores:
                initial_qty = (
                    Decimal(random.randint(1, 4))  # baixo de propósito
                    if idx % 4 == 0
                    else Decimal(random.randint(20, 80))
                )
                session.add(
                    StockMovement(
                        product_id=product.id,
                        quantity=initial_qty,
                        type=MovementType.ENTRADA,
                        reason=MovementReason.AJUSTE_INVENTARIO,
                        observations="Estoque inicial (seed)",
                        company_id=company.id,
                        store_id=store.id,
                        created_by=admin.id,
                    )
                )
        session.flush()

        # ---------- Clientes ----------
        customers = []
        for idx, name in enumerate(CUSTOMER_NAMES, start=1):
            customer = Customer(
                name=name,
                customer_type=CustomerType.FISICA,
                document=f"{idx:011d}",
                ie_indicator=StateRegistrationIndicator.NAO_CONTRIBUINTE,
                company_id=company.id,
                is_active=True,
                created_by=admin.id,
            )
            session.add(customer)
            session.flush()
            customers.append(customer)

        # ---------- Vendas distribuídas em 30 dias ----------
        for _ in range(120):
            days_ago = random.randint(0, 29)
            sale_date = _dt_days_ago(days_ago)
            store = random.choice(stores)
            status = SALE_STATUS_CONCLUIDA if random.random() > 0.08 else SALE_STATUS_CANCELADA

            chosen_products = random.sample(products, k=random.randint(1, 4))
            items_data = [
                (p, random.randint(1, 5)) for p in chosen_products
            ]
            total = sum(p.sale_price * qty for p, qty in items_data)

            sale = Sale(
                customer_id=random.choice(customers).id if random.random() > 0.15 else None,
                user_id=admin.id,
                sale_date=sale_date,
                total_amount=total,
                discount_amount=Decimal("0.00"),
                payment_method=random.choice(PAYMENT_METHODS),
                status=status,
                company_id=company.id,
                store_id=store.id,
                created_by=admin.id,
            )
            session.add(sale)
            session.flush()

            for product, qty in items_data:
                session.add(
                    SaleItem(
                        sale_id=sale.id,
                        product_id=product.id,
                        quantity=qty,
                        unit_price=product.sale_price,
                    )
                )
                if status == SALE_STATUS_CONCLUIDA:
                    session.add(
                        StockMovement(
                            product_id=product.id,
                            quantity=Decimal(qty),
                            type=MovementType.SAIDA,
                            reason=MovementReason.VENDA,
                            source_sale_id=sale.id,
                            company_id=company.id,
                            store_id=store.id,
                            created_by=admin.id,
                        )
                    )
        session.flush()

        # ---------- Compras distribuídas no mesmo período ----------
        for i in range(10):
            days_ago = random.randint(0, 29)
            entry_date = _dt_days_ago(days_ago)
            store = random.choice(stores)
            supplier = random.choice(suppliers)
            chosen_products = random.sample(products, k=random.randint(2, 5))

            items_data = [
                (p, Decimal(random.randint(10, 40))) for p in chosen_products
            ]
            total = sum(p.cost_price * qty for p, qty in items_data)

            purchase = PurchaseOrder(
                supplier_id=supplier.id,
                user_id=admin.id,
                invoice_number=f"{1000 + i}",
                invoice_series="1",
                entry_date=entry_date,
                total_amount=total,
                status=PurchaseStatus.CONFIRMADO,
                company_id=company.id,
                store_id=store.id,
                created_by=admin.id,
            )
            session.add(purchase)
            session.flush()

            for product, qty in items_data:
                total_cost = product.cost_price * qty
                session.add(
                    PurchaseItem(
                        purchase_order_id=purchase.id,
                        product_id=product.id,
                        quantity=qty,
                        unit_cost=product.cost_price,
                        total_cost=total_cost,
                    )
                )
                session.add(
                    StockMovement(
                        product_id=product.id,
                        quantity=qty,
                        type=MovementType.ENTRADA,
                        reason=MovementReason.COMPRA,
                        company_id=company.id,
                        store_id=store.id,
                        created_by=admin.id,
                    )
                )

        session.commit()
        print("Seed concluído.")
        print(f"  Empresa: {company.legal_name} (id={company.id})")
        print(f"  Lojas: {[s.name for s in stores]}")
        print("  Login admin: admin@pyerp.local / senha: Admin123!")
        print(f"  {len(products)} produtos, {len(customers)} clientes")
        print("  120 vendas e 10 compras distribuídas nos últimos 30 dias")


if __name__ == "__main__":
    seed()