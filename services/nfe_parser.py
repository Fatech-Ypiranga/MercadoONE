"""NF-e layout 4.00 XML parser for supplier purchase notes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from xml.etree import ElementTree as ET

from services.exceptions import ValidationError

NFE_NS = "http://www.portalfiscal.inf.br/nfe"
NS = {"nfe": NFE_NS}


@dataclass
class ParsedNfeSupplier:
    document: str
    name: str
    trade_name: str | None
    state_registration: str | None


@dataclass
class ParsedNfeInvoice:
    access_key: str
    invoice_number: str
    invoice_series: str
    issue_date: datetime
    total_amount: Decimal


@dataclass
class ParsedNfeItem:
    line_number: int
    supplier_product_code: str
    barcode: str | None
    name: str
    ncm: str
    unit: str
    quantity: Decimal
    unit_cost: Decimal
    product_total: Decimal
    discount: Decimal
    ipi_amount: Decimal
    icms_st_amount: Decimal


@dataclass
class ParsedNfe:
    supplier: ParsedNfeSupplier
    invoice: ParsedNfeInvoice
    items: list[ParsedNfeItem]


def _text(element: ET.Element | None, tag: str, default: str = "") -> str:
    if element is None:
        return default
    child = element.find(f"nfe:{tag}", NS)
    return (child.text or default).strip() if child is not None else default


def _decimal(value: str, default: str = "0") -> Decimal:
    raw = (value or default).replace(",", ".")
    return Decimal(raw)


def _parse_datetime(value: str) -> datetime:
    if not value:
        raise ValidationError("Invoice issue date not found in XML.")
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(f"Invalid issue date in XML: {value}") from exc


def _find_inf_nfe(root: ET.Element) -> ET.Element:
    inf = root.find(".//nfe:infNFe", NS)
    if inf is None:
        inf = root.find(".//{http://www.portalfiscal.inf.br/nfe}infNFe")
    if inf is None:
        raise ValidationError("Invalid NF-e XML: infNFe tag not found.")
    return inf


def _extract_access_key(inf_nfe: ET.Element, root: ET.Element) -> str:
    raw_id = inf_nfe.attrib.get("Id", "")
    if raw_id.startswith("NFe") and len(raw_id) >= 47:
        return raw_id[3:47]

    ch_nfe = root.find(".//nfe:chNFe", NS)
    if ch_nfe is not None and ch_nfe.text:
        return ch_nfe.text.strip()
    raise ValidationError("Access key not found in XML.")


def _extract_tax_amount(det: ET.Element, tax_tag: str, value_tag: str) -> Decimal:
    for imposto in det.findall("nfe:imposto", NS):
        for node in imposto.iter():
            if node.tag.endswith(tax_tag):
                for child in node.iter():
                    if child.tag.endswith(value_tag) and child.text:
                        return _decimal(child.text)
    return Decimal("0")


def parse_nfe_xml(xml_content: str | bytes) -> ParsedNfe:
    if isinstance(xml_content, bytes):
        xml_content = xml_content.decode("utf-8", errors="replace")

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        raise ValidationError(f"Malformed XML: {exc}") from exc

    inf_nfe = _find_inf_nfe(root)
    ide = inf_nfe.find("nfe:ide", NS)
    emit = inf_nfe.find("nfe:emit", NS)
    if ide is None or emit is None:
        raise ValidationError("Invalid NF-e XML: ide or emit section missing.")

    document = _text(emit, "CNPJ") or _text(emit, "CPF")
    if not document:
        raise ValidationError("Supplier document (CNPJ) not found in XML.")

    supplier = ParsedNfeSupplier(
        document=document,
        name=_text(emit, "xNome"),
        trade_name=_text(emit, "xFant") or None,
        state_registration=_text(emit, "IE") or None,
    )

    access_key = _extract_access_key(inf_nfe, root)
    issue_date = _parse_datetime(_text(ide, "dhEmi") or _text(ide, "dEmi"))
    total_node = inf_nfe.find(".//nfe:ICMSTot/nfe:vNF", NS)
    total_amount = _decimal(total_node.text if total_node is not None else "0")

    items: list[ParsedNfeItem] = []
    for det in inf_nfe.findall("nfe:det", NS):
        line_number = int(det.attrib.get("nItem", len(items) + 1))
        prod = det.find("nfe:prod", NS)
        if prod is None:
            continue

        barcode = _text(prod, "cEAN")
        if barcode.upper() in ("", "SEM GTIN"):
            barcode = None

        quantity = _decimal(_text(prod, "qCom", "0"))
        unit_cost = _decimal(_text(prod, "vUnCom", "0"))
        product_total = _decimal(_text(prod, "vProd", "0"))
        discount = _decimal(_text(prod, "vDesc", "0"))
        ipi_amount = _extract_tax_amount(det, "IPI", "vIPI")
        icms_st_amount = _extract_tax_amount(det, "ICMS", "vICMSST")

        items.append(
            ParsedNfeItem(
                line_number=line_number,
                supplier_product_code=_text(prod, "cProd"),
                barcode=barcode,
                name=_text(prod, "xProd"),
                ncm=_text(prod, "NCM"),
                unit=_text(prod, "uCom", "UN"),
                quantity=quantity,
                unit_cost=unit_cost,
                product_total=product_total,
                discount=discount,
                ipi_amount=ipi_amount,
                icms_st_amount=icms_st_amount,
            )
        )

    if not items:
        raise ValidationError("NF-e XML does not contain any items.")

    invoice = ParsedNfeInvoice(
        access_key=access_key,
        invoice_number=_text(ide, "nNF"),
        invoice_series=_text(ide, "serie", "1"),
        issue_date=issue_date,
        total_amount=total_amount,
    )

    return ParsedNfe(supplier=supplier, invoice=invoice, items=items)


def calculate_entry_unit_cost(item: ParsedNfeItem) -> Decimal:
    if item.quantity <= 0:
        raise ValidationError(f"Invalid quantity for item {item.supplier_product_code}.")
    numerator = item.product_total - item.discount + item.ipi_amount + item.icms_st_amount
    return (numerator / item.quantity).quantize(Decimal("0.01"))
