import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { mergeCepSuccess, shouldApplyCepResult } from "./apply-cep-result.ts";

const baseForm = {
  description: "Principal",
  zip_code: "01310-100",
  street: "",
  number: "42",
  complement: "Sala 1",
  neighborhood: "",
  city: "",
  state: "",
  ibge_code: "",
};

describe("shouldApplyCepResult", () => {
  it("rejects stale request generations", () => {
    assert.equal(
      shouldApplyCepResult({
        requestId: 1,
        latestRequestId: 2,
        lookedUpDigits: "01310100",
        currentZipCode: "01310100",
      }),
      false,
    );
  });

  it("rejects when the current CEP no longer matches the lookup", () => {
    assert.equal(
      shouldApplyCepResult({
        requestId: 2,
        latestRequestId: 2,
        lookedUpDigits: "01310100",
        currentZipCode: "22041080",
      }),
      false,
    );
  });

  it("accepts the latest matching CEP response", () => {
    assert.equal(
      shouldApplyCepResult({
        requestId: 3,
        latestRequestId: 3,
        lookedUpDigits: "01310100",
        currentZipCode: "01310-100",
      }),
      true,
    );
  });
});

describe("mergeCepSuccess", () => {
  it("preserves number, complement, description and zip formatting", () => {
    const merged = mergeCepSuccess(baseForm, {
      street: "Avenida Paulista",
      neighborhood: "Bela Vista",
      city: "São Paulo",
      state: "SP",
      ibge_code: "3550308",
    });

    assert.equal(merged.number, "42");
    assert.equal(merged.complement, "Sala 1");
    assert.equal(merged.description, "Principal");
    assert.equal(merged.zip_code, "01310-100");
    assert.equal(merged.street, "Avenida Paulista");
    assert.equal(merged.ibge_code, "3550308");
  });
});
