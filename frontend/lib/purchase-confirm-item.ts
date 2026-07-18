/** Minimal preview item fields needed to build a purchase confirm line. */
export type PreviewConfirmItem = {
  supplier_product_code: string;
  quantity: string | number;
  unit_cost: string | number;
  entry_unit_cost: string | number;
  discount: string | number;
  ipi_amount: string | number;
  icms_st_amount: string | number;
  total_cost: string | number;
  name: string;
  barcode?: string | null;
  unit: string;
  ncm: string;
  suggested_product_id?: number | null;
};

export type ConfirmItemMapping = {
  product_id: string;
  create_new: boolean;
  new_sku: string;
  category_id: string;
};

/**
 * Builds one PurchaseConfirmItemInput from NF-e preview data.
 * Persisted `unit_cost` must be entry_unit_cost (includes discount/IPI/ICMS-ST),
 * matching the value shown in the UI and used for new-product cost.
 */
export function buildConfirmItemPayload(
  item: PreviewConfirmItem,
  map?: ConfirmItemMapping,
) {
  const base = {
    supplier_product_code: item.supplier_product_code,
    quantity: item.quantity,
    unit_cost: item.entry_unit_cost,
    discount: item.discount,
    ipi_amount: item.ipi_amount,
    icms_st_amount: item.icms_st_amount,
    total_cost: item.total_cost,
  };

  if (map?.create_new) {
    return {
      ...base,
      product_id: null,
      create_product: {
        name: item.name,
        sku: map.new_sku || item.supplier_product_code,
        barcode: item.barcode ?? null,
        category_id: Number(map.category_id),
        cost_price: item.entry_unit_cost,
        sale_price: item.entry_unit_cost,
        unit_of_measure:
          item.unit === "KG" ? "KG" : item.unit === "CX" ? "CX" : "UN",
        ncm: item.ncm || null,
      },
    };
  }

  return {
    ...base,
    product_id: Number(map?.product_id || item.suggested_product_id),
    create_product: null,
  };
}
