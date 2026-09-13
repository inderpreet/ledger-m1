"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { accountHex } from "@/lib/accountStyle";
import { formatDateWithDay, formatMoney } from "@/lib/format";
import type { CashflowPayload } from "@/lib/types";

export function BalanceChart({ data }: { data: CashflowPayload }) {
  const chartRows = data.rows.map((row) => {
    const point: Record<string, string | number> = { date: String(row.date) };
    for (const account of data.accounts) {
      point[account.name] = Number(row[String(account.id)]);
    }
    point.Combined = Number(row.combined);
    return point;
  });

  const series = [...data.accounts.map((a) => a.name), "Combined"];

  return (
    <div className="h-80 w-full rounded-lg border border-rule bg-card p-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartRows} margin={{ top: 8, right: 12, left: 8, bottom: 0 }}>
          <CartesianGrid stroke="#e4ddd0" strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            minTickGap={28}
            tickFormatter={(value) => formatDateWithDay(String(value))}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            tickFormatter={(v) =>
              new Intl.NumberFormat("en-CA", { notation: "compact" }).format(Number(v))
            }
          />
          <Tooltip
            labelFormatter={(label) => formatDateWithDay(String(label))}
            formatter={(value) => formatMoney(Number(value))}
          />
          <Legend />
          {series.map((name) => (
            <Line
              key={name}
              type="monotone"
              dataKey={name}
              stroke={accountHex(name)}
              strokeWidth={name === "Combined" ? 2 : 1.8}
              strokeDasharray={name === "Combined" ? "5 4" : undefined}
              dot={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
