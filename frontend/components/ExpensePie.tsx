"use client";

import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { formatMoney } from "@/lib/format";

const CATEGORY_COLORS: Record<string, string> = {
  "Housing & Debt": "#8b3a2a",
  Insurance: "#2f4a3c",
  Utilities: "#b8862b",
  Subscriptions: "#3d5c7a",
  Uncategorized: "#7a7368",
};

const FALLBACK = ["#c42b2b", "#187a3c", "#1c2218", "#6b4f2a", "#4a6670", "#a14a32"];

function colorFor(category: string, index: number): string {
  return CATEGORY_COLORS[category] ?? FALLBACK[index % FALLBACK.length];
}

export function ExpensePie({
  rows,
}: {
  rows: { category: string; amount: number }[];
}) {
  const data = rows.filter((row) => row.amount > 0);
  const total = data.reduce((sum, row) => sum + row.amount, 0);

  if (data.length === 0) {
    return (
      <div className="flex h-80 items-center justify-center rounded-lg border border-rule bg-card px-4 text-sm text-ink/50">
        No expenses in this window.
      </div>
    );
  }

  return (
    <div className="h-80 w-full rounded-lg border border-rule bg-card p-4">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="amount"
            nameKey="category"
            cx="50%"
            cy="46%"
            innerRadius={52}
            outerRadius={88}
            paddingAngle={1.5}
            stroke="#fbf8f1"
          >
            {data.map((row, i) => (
              <Cell key={row.category} fill={colorFor(row.category, i)} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value, name) => {
              const amount = Number(value);
              const pct = total ? ((amount / total) * 100).toFixed(1) : "0.0";
              return [`${formatMoney(amount)} (${pct}%)`, String(name)];
            }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
