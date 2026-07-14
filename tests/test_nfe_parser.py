from decimal import Decimal
from pathlib import Path

import pytest

from services.exceptions import ValidationError
from services.nfe_parser import calculate_entry_unit_cost, parse_nfe_xml

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "nfe"


def test_parse_valid_nfe_xml():
    xml = (FIXTURES_DIR / "ci_sample_01.xml").read_text(encoding="utf-8")
    parsed = parse_nfe_xml(xml)

    assert parsed.supplier.document == "20202020000120"
    assert parsed.supplier.name == "LimpezaTotal Profissional"
    assert parsed.invoice.access_key.endswith("3")
    assert len(parsed.items) == 6
    assert parsed.items[0].supplier_product_code == "011-LIM-DET-001"
    assert parsed.items[0].barcode == "7890011000100"


def test_calculate_entry_unit_cost():
    xml = (FIXTURES_DIR / "ci_sample_01.xml").read_text(encoding="utf-8")
    item = parse_nfe_xml(xml).items[0]
    entry_cost = calculate_entry_unit_cost(item)
    assert entry_cost == Decimal("2.75")


def test_parse_malformed_xml_raises_validation_error():
    with pytest.raises(ValidationError, match="Malformed XML"):
        parse_nfe_xml("<nfeProc><broken>")
