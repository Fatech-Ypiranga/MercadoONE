import assert from "node:assert/strict";
import { test } from "node:test";

import { salesByDay, salesByPaymentMethod } from "./dashboard-metrics.ts";

const today = new Date(2026, 10, 23, 15, 0, 0);

test("salesByDay preenche dias sem venda e ignora canceladas", () => {
  const points = salesByDay(
    [
      { total_amount: "10.50", status: "Concluida", sale_date: new Date(2026, 10, 23, 9).toISOString() },
      { total_amount: "4.50", status: "Concluida", sale_date: new Date(2026, 10, 23, 18).toISOString() },
      { total_amount: "99", status: "Cancelada", sale_date: new Date(2026, 10, 22, 9).toISOString() },
      { total_amount: "7", status: "Concluida", sale_date: new Date(2026, 10, 21, 9).toISOString() },
      { total_amount: "1000", status: "Concluida", sale_date: new Date(2026, 9, 1, 9).toISOString() },
    ],
    3,
    today,
  );
  assert.deepEqual(
    points.map((p) => [p.label, p.revenue, p.count]),
    [
      ["21/11", 7, 1],
      ["22/11", 0, 0],
      ["23/11", 15, 2],
    ],
  );
});

test("salesByPaymentMethod agrupa, rotula e ordena por receita", () => {
  const slices = salesByPaymentMethod([
    { total_amount: "10", status: "Concluida", payment_method: "pix" },
    { total_amount: "30", status: "Concluida", payment_method: "PIX" },
    { total_amount: "5", status: "Concluida", payment_method: null },
    { total_amount: "50", status: "Cancelada", payment_method: "dinheiro" },
    { total_amount: "20", status: "Concluida", payment_method: "dinheiro" },
  ]);
  assert.deepEqual(
    slices.map((s) => [s.label, s.revenue, s.count]),
    [
      ["PIX", 40, 2],
      ["Dinheiro", 20, 1],
      ["Não informado", 5, 1],
    ],
  );
});

test("salesByPaymentMethod soma por pagamento quando a venda é dividida", () => {
  const slices = salesByPaymentMethod([
    {
      total_amount: "100",
      status: "Concluida",
      payment_method: "multiplo",
      payments: [
        { method: "dinheiro", amount: "30.00" },
        { method: "pix", amount: "70.00" },
      ],
    },
    { total_amount: "20", status: "Concluida", payment_method: "pix", payments: [] },
  ]);
  assert.deepEqual(
    slices.map((s) => [s.label, s.revenue, s.count]),
    [
      ["PIX", 90, 2],
      ["Dinheiro", 30, 1],
    ],
  );
});
