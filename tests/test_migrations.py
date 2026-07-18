from sqlalchemy import inspect, text

from alembic import command
from database.migrate import get_alembic_config, upgrade_head


def test_alembic_upgrade_creates_all_tables(test_engine):
    upgrade_head(test_engine.url.render_as_string(hide_password=False))

    inspector = inspect(test_engine)
    tables = set(inspector.get_table_names())

    expected = {
        "alembic_version",
        "audit_log",
        "branches",
        "categories",
        "companies",
        "customer_addresses",
        "customers",
        "product_fiscals",
        "product_material_sequences",
        "products",
        "purchase_items",
        "purchase_orders",
        "sale_items",
        "sales",
        "stock_movements",
        "stores",
        "supplier_addresses",
        "supplier_municipalities",
        "supplier_product_mappings",
        "supplier_sequences",
        "suppliers",
        "users",
    }
    assert expected.issubset(tables)
    assert "brands" not in tables

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    assert {"pdv_id", "pdv_pin_hash"}.issubset(user_columns)
    sale_columns = {column["name"] for column in inspector.get_columns("sales")}
    assert "discount_amount" in sale_columns


def test_epic4_migration_backfills_codes_infers_supplier_and_cycles(test_engine):
    database_url = test_engine.url.render_as_string(hide_password=False)
    config = get_alembic_config(database_url)
    command.downgrade(config, "f6a7b8c9d0e1")

    with test_engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO companies (id, legal_name, trade_name, document, is_active, created_at, updated_at)
                VALUES (9001, 'Migration Company', 'Migration', '90000000000100', true, now(), now())
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO categories (id, name, slug, is_active, created_at, updated_at, company_id)
                VALUES (9001, 'Migration Category', 'migration-category', true, now(), now(), 9001)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO suppliers (
                    id, name, document, is_active, created_at, updated_at, company_id, code
                )
                VALUES (9001, 'Migration Supplier', '90000000000101', true, now(), now(), 9001, '35001001')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO products (
                    id, name, sku, is_active, cost_price, sale_price, unit_of_measure,
                    category_id, created_at, updated_at, company_id
                )
                VALUES
                    (9001, 'First', 'MIG-1', true, 1, 2, 'UN', 9001, now(), now(), 9001),
                    (9002, 'Second', 'MIG-2', true, 1, 2, 'UN', 9001, now(), now(), 9001)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO supplier_product_mappings (
                    supplier_id, supplier_product_code, product_id, created_at
                )
                VALUES (9001, 'SUP-1', 9001, now())
                """
            )
        )

    command.upgrade(config, "head")
    with test_engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT id, material_code, primary_supplier_id
                FROM products
                WHERE id IN (9001, 9002)
                ORDER BY id
                """
            )
        ).all()
    assert rows == [(9001, "0000001", 9001), (9002, "0000002", None)]

    command.downgrade(config, "f6a7b8c9d0e1")
    assert "brands" in inspect(test_engine).get_table_names()
    command.upgrade(config, "head")
    assert "brands" not in inspect(test_engine).get_table_names()
