"""Minimal catalog seed for purchase/XML tests (aligned with tests/fixtures/nfe)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import Session, select

from database.seed import ensure_demo_organization
from models.category import Category
from models.product import Brand, Product, ProductFiscal, UnitOfMeasure

# Products matching barcodes in tests/fixtures/nfe/ci_sample_01.xml
_CI_SAMPLE_01_PRODUCTS = (
    ("LIM-DET-001", "7890011000100", "Detergente Líquido 500ml", "34022000"),
    ("LIM-ESP-005", "7890011000500", "Esponja Dupla Face", "68053090"),
    ("LIM-AMA-004", "7890011000400", "Amaciante 2L", "38099190"),
    ("LIM-LIM-010", "7890011001000", "Limpador Multiuso 500ml", "34025000"),
    ("LIM-DES-003", "7890011000300", "Desinfetante 2L", "38089419"),
    ("LIM-SAP-006", "7890011000600", "Saponáceo em Pó 300g", "34054000"),
)


def seed_purchase_test_catalog(db: Session) -> None:
    """Create category + products needed for ci_sample_01 purchase mapping tests."""
    company, _, _ = ensure_demo_organization(db)
    company_id = company.id

    category = db.exec(
        select(Category).where(
            Category.slug == "limpeza",
            Category.company_id == company_id,
        )
    ).first()
    if not category:
        now = datetime.now(timezone.utc)
        category = Category(
            name="Limpeza",
            slug="limpeza",
            is_active=True,
            company_id=company_id,
            created_at=now,
            updated_at=now,
        )
        db.add(category)
        db.flush()

    brand = db.exec(
        select(Brand).where(Brand.name == "LimpezaTotal", Brand.company_id == company_id)
    ).first()
    if not brand:
        brand = Brand(name="LimpezaTotal", company_id=company_id)
        db.add(brand)
        db.flush()

    now = datetime.now(timezone.utc)
    for sku, barcode, name, ncm in _CI_SAMPLE_01_PRODUCTS:
        existing = db.exec(
            select(Product).where(Product.sku == sku, Product.company_id == company_id)
        ).first()
        if existing:
            continue

        cost = Decimal("2.50")
        product = Product(
            name=name,
            sku=sku,
            barcode=barcode,
            description="Produto mínimo para testes de compra/XML",
            is_active=True,
            cost_price=cost,
            sale_price=(cost * Decimal("1.35")).quantize(Decimal("0.01")),
            unit_of_measure=UnitOfMeasure.UN,
            category_id=category.id,
            brand_id=brand.id,
            company_id=company_id,
            created_at=now,
            updated_at=now,
        )
        db.add(product)
        db.flush()
        db.add(
            ProductFiscal(
                product_id=product.id,
                ncm=ncm,
                cfop_default="5102",
                origem_produto=0,
            )
        )

    db.commit()
