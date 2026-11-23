"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { EmptyState } from "@/components/ui-states";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { DailyRevenuePoint, PaymentSlice } from "@/lib/dashboard-metrics";
import { formatMoney } from "@/lib/format";

const TOOLTIP_STYLE = {
  background: "var(--color-card)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-md)",
  fontSize: 12.5,
  boxShadow: "0 8px 20px -6px oklch(0.2 0.02 260 / 20%)",
};
const TICK_STYLE = { fill: "var(--color-muted-foreground)", fontSize: 12 };
// Variáveis --chart-N trocam de paleta no modo daltônico (ver globals.css).
const SLICE_COLORS = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
];

export function RevenueByDayChart({
  data,
  loading,
  periodHint,
}: {
  data: DailyRevenuePoint[];
  loading?: boolean;
  periodHint: string;
}) {
  const total = data.reduce((sum, p) => sum + p.revenue, 0);
  const summary = data.map((p) => `${p.label}: ${formatMoney(p.revenue)}`).join("; ");
  return (
    <Card>
      <CardHeader className="border-b">
        <CardTitle>Receita por dia</CardTitle>
        <CardDescription>{periodHint}</CardDescription>
      </CardHeader>
      <CardContent className="pt-(--card-spacing)">
        {loading ? (
          <div className="h-56 animate-pulse rounded-md bg-muted" aria-hidden />
        ) : total === 0 ? (
          <EmptyState message="Sem vendas no período." />
        ) : (
          <div role="img" aria-label={`Receita por dia. ${summary}`}>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={data} margin={{ left: 4, right: 12, top: 8, bottom: 4 }}>
                <CartesianGrid vertical={false} stroke="var(--color-border)" />
                <XAxis dataKey="label" tick={TICK_STYLE} axisLine={false} tickLine={false} />
                <YAxis
                  tick={TICK_STYLE}
                  axisLine={false}
                  tickLine={false}
                  width={56}
                  tickFormatter={(v: number) => formatMoney(v).replace(/\s?,00$/, "")}
                />
                <Tooltip
                  cursor={{ fill: "var(--color-muted)" }}
                  contentStyle={TOOLTIP_STYLE}
                  formatter={(value, _name, item) => [
                    formatMoney(Number(value)),
                    `Receita (${(item?.payload as DailyRevenuePoint | undefined)?.count ?? 0} vendas)`,
                  ]}
                />
                <Bar
                  dataKey="revenue"
                  fill="var(--color-chart-1)"
                  radius={[4, 4, 0, 0]}
                  maxBarSize={36}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function PaymentMethodChart({
  data,
  loading,
  periodHint,
}: {
  data: PaymentSlice[];
  loading?: boolean;
  periodHint: string;
}) {
  const summary = data.map((s) => `${s.label}: ${formatMoney(s.revenue)}`).join("; ");
  return (
    <Card>
      <CardHeader className="border-b">
        <CardTitle>Formas de pagamento</CardTitle>
        <CardDescription>{periodHint}</CardDescription>
      </CardHeader>
      <CardContent className="pt-(--card-spacing)">
        {loading ? (
          <div className="h-56 animate-pulse rounded-md bg-muted" aria-hidden />
        ) : !data.length ? (
          <EmptyState message="Sem vendas no período." />
        ) : (
          <div role="img" aria-label={`Receita por forma de pagamento. ${summary}`}>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={data}
                  dataKey="revenue"
                  nameKey="label"
                  innerRadius={52}
                  outerRadius={84}
                  paddingAngle={2}
                  stroke="var(--color-card)"
                >
                  {data.map((slice, i) => (
                    <Cell key={slice.method} fill={SLICE_COLORS[i % SLICE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={TOOLTIP_STYLE}
                  formatter={(value, name, item) => [
                    formatMoney(Number(value)),
                    `${name} (${(item?.payload as PaymentSlice | undefined)?.count ?? 0} vendas)`,
                  ]}
                />
                <Legend
                  verticalAlign="bottom"
                  wrapperStyle={{ fontSize: 12, color: "var(--color-muted-foreground)" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
