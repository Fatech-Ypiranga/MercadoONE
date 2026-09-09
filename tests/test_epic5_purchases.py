import re

from fastapi.testclient import TestClient
from sqlmodel import Session, func, select

from models.product import Product
from models.purchase import PurchaseOrder, SupplierProductMapping
from models.stock_movement import StockMovement
from models.supplier import Supplier, SupplierAddress, SupplierMunicipality, SupplierSequence
from shared.audit import AuditLog

VALID_DOCUMENT = "11222333000181"
VALID_ADDRESS = {
    "description": "Principal",
    "zip_code": "01310100",
    "street": "Avenida Paulista",
    "number": "1000",
    "complement": "Sala 1",
    "neighborhood": "Bela Vista",
    "city": "São Paulo",
    "state": "SP",
    "ibge_code": "3550308",
}


def _confirm_payload(category_id: int, **overrides) -> dict:
    payload = {
        "access_key": "EPIC5-VALID-0001",
        "invoice_number": "5001",
        "invoice_series": "1",
        "issue_date": "2026-07-16T12:00:00Z",
        "create_supplier": True,
        "supplier_name": "Fornecedor Épico 5",
        "supplier_trade_name": "Fornecedor E5",
        "supplier_document": VALID_DOCUMENT,
        "supplier_state_registration": "123456",
        "supplier_address": VALID_ADDRESS,
        "items": [
            {
                "supplier_product_code": "CPROD-EP5",
                "quantity": "2",
                "unit_cost": "5.00",
                "total_cost": "10.00",
                "create_product": {
                    "name": "Produto importado Épico 5",
                    "sku": "PUR-EP5-001",
                    "category_id": category_id,
                    "cost_price": "5.00",
                },
            }
        ],
    }
    payload.update(overrides)
    return payload


def _count(session: Session, model) -> int:
    session.expire_all()
    return session.exec(select(func.count()).select_from(model)).one()


def test_preview_includes_complete_or_partial_supplier_address(client: TestClient, seeded_catalog):
    complete_xml = """<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe
      Id="NFe35260711222333000181550010000000011000000010"><ide><nNF>1</nNF>
      <serie>1</serie><dhEmi>2026-07-16T12:00:00-03:00</dhEmi></ide><emit>
      <CNPJ>11222333000181</CNPJ><xNome>Fornecedor</xNome><enderEmit>
      <CEP>01310100</CEP><xLgr>Avenida Paulista</xLgr><nro>1000</nro>
      <xCpl>Sala 1</xCpl><xBairro>Bela Vista</xBairro><xMun>São Paulo</xMun>
      <UF>SP</UF><cMun>3550308</cMun></enderEmit></emit><det nItem="1"><prod>
      <cProd>011-LIM-DET-001</cProd><xProd>Produto</xProd><NCM>12345678</NCM>
      <uCom>UN</uCom><qCom>1</qCom><vUnCom>1</vUnCom><vProd>1</vProd>
      </prod></det><total><ICMSTot><vNF>1</vNF></ICMSTot></total></infNFe></NFe>"""
    partial_xml = re.sub(
        r"<enderEmit>.*?</enderEmit>",
        "<enderEmit><xLgr>Rua Parcial</xLgr></enderEmit>",
        complete_xml,
        flags=re.DOTALL,
    )

    complete = client.post(
        "/purchases/upload-xml",
        files={"file": ("complete.xml", complete_xml, "application/xml")},
    )
    partial = client.post(
        "/purchases/upload-xml",
        files={"file": ("partial.xml", partial_xml, "application/xml")},
    )

    assert complete.status_code == 200
    assert complete.json()["supplier"]["address"] == {
        key: value for key, value in VALID_ADDRESS.items() if key != "description"
    }
    assert partial.status_code == 200
    assert partial.json()["supplier"]["address"]["street"] == "Rua Parcial"
    assert partial.json()["supplier"]["address"]["zip_code"] is None


def test_new_supplier_requires_address_without_side_effects(
    client: TestClient, category: dict, db_session: Session
):
    models = (
        Supplier,
        PurchaseOrder,
        Product,
        AuditLog,
        StockMovement,
        SupplierProductMapping,
    )
    before = {model: _count(db_session, model) for model in models}
    response = client.post(
        "/purchases/confirm",
        json=_confirm_payload(category["id"], supplier_address=None),
    )

    assert response.status_code == 422
    for model in models:
        assert _count(db_session, model) == before[model]


def test_manually_completed_address_creates_valid_supplier_and_inline_product(
    client: TestClient, category: dict
):
    response = client.post("/purchases/confirm", json=_confirm_payload(category["id"]))

    assert response.status_code == 201
    supplier = client.get(f"/suppliers/{response.json()['supplier_id']}").json()
    assert supplier["document"] == VALID_DOCUMENT
    assert supplier["address"]["complement"] == "Sala 1"
    assert supplier["address"]["ibge_code"] == "3550308"
    assert re.fullmatch(r"\d{8}", supplier["code"])
    product_id = response.json()["items"][0]["product_id"]
    product = client.get(f"/products/{product_id}").json()
    assert re.fullmatch(r"\d{7}", product["material_code"])
    assert product["primary_supplier_id"] == supplier["id"]


def test_invalid_supplier_data_rolls_back_all_side_effects(
    client: TestClient, category: dict, db_session: Session
):
    models = (Supplier, PurchaseOrder, Product, AuditLog)
    before = {model: _count(db_session, model) for model in models}
    invalid_cnpj = client.post(
        "/purchases/confirm",
        json=_confirm_payload(category["id"], supplier_document="11222333000182"),
    )
    mismatch = client.post(
        "/purchases/confirm",
        json=_confirm_payload(
            category["id"],
            access_key="EPIC5-INVALID-UF-0002",
            supplier_document="12345678000195",
            supplier_address={**VALID_ADDRESS, "state": "RJ"},
        ),
    )

    assert invalid_cnpj.status_code == 422
    assert mismatch.status_code == 422
    for model in models:
        assert _count(db_session, model) == before[model]


def test_existing_supplier_is_reused_without_address_overwrite(
    client: TestClient, category: dict, supplier: dict
):
    response = client.post(
        "/purchases/confirm",
        json=_confirm_payload(
            category["id"],
            supplier_document="11.222.333/0001-81",
            supplier_address={**VALID_ADDRESS, "number": "9999"},
        ),
    )

    assert response.status_code == 201
    persisted = client.get(f"/suppliers/{supplier['id']}").json()
    assert persisted["address"]["number"] == "1000"


def test_supplier_id_and_create_supplier_is_rejected(
    client: TestClient, category: dict, supplier: dict
):
    response = client.post(
        "/purchases/confirm",
        json=_confirm_payload(
            category["id"],
            supplier_id=supplier["id"],
            create_supplier=True,
        ),
    )

    assert response.status_code == 422


def test_foreign_supplier_id_is_hidden_and_cross_tenant_document_not_reused(
    client: TestClient,
    second_company_client: TestClient,
    category: dict,
):
    foreign = second_company_client.post(
        "/suppliers/",
        json={
            "name": "Fornecedor estrangeiro",
            "document": VALID_DOCUMENT,
            "address": VALID_ADDRESS,
        },
    ).json()

    hidden = client.post(
        "/purchases/confirm",
        json=_confirm_payload(
            category["id"],
            supplier_id=foreign["id"],
            create_supplier=False,
        ),
    )
    local = client.post("/purchases/confirm", json=_confirm_payload(category["id"]))

    assert hidden.status_code == 404
    assert local.status_code == 201
    assert local.json()["supplier_id"] != foreign["id"]


def test_later_item_failure_rolls_back_supplier_product_and_related_rows(
    client: TestClient, category: dict, db_session: Session
):
    models = (
        Supplier,
        SupplierAddress,
        SupplierMunicipality,
        SupplierSequence,
        PurchaseOrder,
        Product,
        AuditLog,
        StockMovement,
        SupplierProductMapping,
    )
    before = {model: _count(db_session, model) for model in models}
    first_item = _confirm_payload(category["id"])["items"][0]
    response = client.post(
        "/purchases/confirm",
        json=_confirm_payload(
            category["id"],
            items=[
                first_item,
                {
                    "supplier_product_code": "FAIL-AFTER-FIRST",
                    "quantity": "1",
                    "unit_cost": "2.00",
                    "total_cost": "2.00",
                },
            ],
        ),
    )

    assert response.status_code == 422
    for model in models:
        assert _count(db_session, model) == before[model]
