from sqlalchemy import inspect

from database.migrate import upgrade_head


def test_alembic_upgrade_creates_all_tables(test_engine):
    upgrade_head(test_engine.url.render_as_string(hide_password=False))

    inspector = inspect(test_engine)
    tables = set(inspector.get_table_names())

    expected = {
        "alembic_version",
        "audit_log",
        "branches",
        "brands",
        "categories",
        "companies",
        "customer_addresses",
        "customers",
        "product_fiscals",
        "products",
        "purchase_items",
        "purchase_orders",
        "sale_items",
        "sales",
        "stock_movements",
        "stores",
        "supplier_product_mappings",
        "suppliers",
        "users",
    }
    assert expected.issubset(tables)
