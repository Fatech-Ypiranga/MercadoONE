import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { buildConfirmItemPayload } from "./purchase-confirm-item.ts";

const previewItem = {
  supplier_product_code: "011-LIM-ESP-005",
  quantity: "14.000",
  unit_cost: "3.80",
  entry_unit_cost: "3.79",
  discount: "0.15",
  ipi_amount: "0.00",
  icms_st_amount: "0.00",
  total_cost: "52.99",
  name: "Esponja Dupla Face",
  barcode: "7890011000500",
  unit: "UN",
  ncm: "68053090",
  suggested_product_id: 42,
};

describe("buildConfirmItemPayload", () => {
  it("sends entry_unit_cost as unit_cost when raw unit_cost differs", () => {
    assert.notEqual(previewItem.unit_cost, previewItem.entry_unit_cost);

    const payload = buildConfirmItemPayload(previewItem, {
      product_id: "42",
      create_new: false,
      new_sku: "",
      category_id: "",
    });

    assert.equal(payload.unit_cost, previewItem.entry_unit_cost);
    assert.equal(payload.discount, previewItem.discount);
    assert.equal(payload.ipi_amount, previewItem.ipi_amount);
    assert.equal(payload.icms_st_amount, previewItem.icms_st_amount);
    assert.equal(payload.total_cost, previewItem.total_cost);
    assert.equal(payload.product_id, 42);
  });

  it("uses entry_unit_cost for create_product cost fields", () => {
    const payload = buildConfirmItemPayload(previewItem, {
      product_id: "",
      create_new: true,
      new_sku: "NEW-SKU",
      category_id: "7",
    });

    assert.equal(payload.unit_cost, previewItem.entry_unit_cost);
    assert.equal(payload.create_product?.cost_price, previewItem.entry_unit_cost);
    assert.equal(payload.create_product?.sale_price, previewItem.entry_unit_cost);
  });
});
