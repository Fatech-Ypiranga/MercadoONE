import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { errorMessage } from "./format.ts";

class FakeApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

describe("errorMessage", () => {
  it("returns the server-provided message for an ApiError", () => {
    const err = new FakeApiError("CNPJ já cadastrado.");
    assert.equal(errorMessage(err), "CNPJ já cadastrado.");
  });

  it("returns a friendly network message for a raw fetch failure, not the raw error text", () => {
    const err = new TypeError("Failed to fetch");
    assert.equal(
      errorMessage(err),
      "Não foi possível conectar à API. Verifique sua conexão e tente novamente.",
    );
  });

  it("falls back to the default message for a non-Error value", () => {
    assert.equal(errorMessage("boom"), "Ocorreu um erro");
  });
});
