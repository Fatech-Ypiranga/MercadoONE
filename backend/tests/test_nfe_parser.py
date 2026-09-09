from decimal import Decimal
from pathlib import Path

import pytest

from services.exceptions import ValidationError
from services.nfe_parser import calculate_entry_unit_cost, parse_nfe_xml


def _nfe_xml(*, address: str = "", n_item: str = "1", quantity: str = "2.000") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<NFe xmlns="http://www.portalfiscal.inf.br/nfe">
  <infNFe Id="NFe35260711222333000181550010000000011000000010" versao="4.00">
    <ide>
      <cUF>35</cUF><nNF>1</nNF><serie>1</serie>
      <dhEmi>2026-07-16T12:00:00-03:00</dhEmi>
    </ide>
    <emit>
      <CNPJ>11.222.333/0001-81</CNPJ>
      <xNome>Fornecedor Épico 5</xNome>
      <xFant></xFant>
      <IE>123456</IE>
      {address}
    </emit>
    <det nItem="{n_item}">
      <prod>
        <cProd>EP5-001</cProd><cEAN>SEM GTIN</cEAN><xProd>Produto</xProd>
        <NCM>12345678</NCM><uCom>UN</uCom><qCom>{quantity}</qCom>
        <vUnCom>5.00</vUnCom><vProd>10.00</vProd>
      </prod>
    </det>
    <total><ICMSTot><vNF>10.00</vNF></ICMSTot></total>
  </infNFe>
</NFe>"""


def test_parser_reads_complete_supplier_address():
    xml = _nfe_xml(
        address="""
        <enderEmit>
          <CEP>01310100</CEP><xLgr>Avenida Paulista</xLgr><nro>1000</nro>
          <xCpl>Sala 1</xCpl><xBairro>Bela Vista</xBairro>
          <xMun>São Paulo</xMun><UF>SP</UF><cMun>3550308</cMun>
        </enderEmit>
        """
    )

    parsed = parse_nfe_xml(xml)

    assert parsed.supplier.address.zip_code == "01310100"
    assert parsed.supplier.address.street == "Avenida Paulista"
    assert parsed.supplier.address.number == "1000"
    assert parsed.supplier.address.complement == "Sala 1"
    assert parsed.supplier.address.neighborhood == "Bela Vista"
    assert parsed.supplier.address.city == "São Paulo"
    assert parsed.supplier.address.state == "SP"
    assert parsed.supplier.address.ibge_code == "3550308"
    assert parsed.supplier.trade_name is None


@pytest.mark.parametrize(
    ("address", "expected_street"),
    [
        ("", None),
        ("<enderEmit><xLgr>Rua Parcial</xLgr><CEP></CEP></enderEmit>", "Rua Parcial"),
    ],
)
def test_parser_permits_missing_or_partial_supplier_address(address, expected_street):
    parsed = parse_nfe_xml(_nfe_xml(address=address))

    assert parsed.supplier.address.street == expected_street
    assert parsed.supplier.address.zip_code is None
    assert parsed.items[0].quantity == Decimal("2.000")


@pytest.mark.parametrize(
    ("field", "value"),
    [("quantity", "not-a-decimal"), ("n_item", "not-an-integer")],
)
def test_parser_maps_malformed_item_numbers_to_validation_error(field, value):
    kwargs = {field: value}

    with pytest.raises(ValidationError):
        parse_nfe_xml(_nfe_xml(**kwargs))


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
