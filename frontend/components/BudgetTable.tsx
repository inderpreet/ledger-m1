"use client";

import { useEffect, useState } from "react";
import { DataTable, type Column } from "@/components/DataTable";
import { api } from "@/lib/api";
import type { BudgetCategory } from "@/lib/categories";
import { formatMoney } from "@/lib/format";

const EMPTY: Record<string, string | number | boolean | null> = {
  name: "",
  amount: "",
  period: "monthly",
};

function payloadFrom(record: Record<string, unknown>) {
  const amountRaw = record.amount;
  return {
    name: String(record.name ?? "").trim(),
    amount: amountRaw === "" || amountRaw === null || amountRaw === undefined ? null : Number(amountRaw),
    period: String(record.period || "monthly"),
  };
}

export function BudgetTable({ onChanged }: { onChanged?: () => void }) {
  const [rows, setRows] = useState<BudgetCategory[]>([]);
  const [draft, setDraft] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const cats = await api.get<BudgetCategory[]>("/api/budget-categories");
    setRows(cats);
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, []);

  const columns: Column<BudgetCategory>[] = [
    { key: "name", label: "Name" },
    {
      key: "amount",
      label: "Amount",
      type: "number",
      render: (row) => <span className="tabular">{formatMoney(row.amount)}</span>,
    },
    {
      key: "period",
      label: "Period",
      type: "select",
      options: [
        { value: "monthly", label: "Monthly" },
        { value: "biweekly", label: "Bi-weekly" },
        { value: "yearly", label: "Yearly" },
      ],
      render: (row) =>
        row.period === "yearly" ? "Yearly" : row.period === "biweekly" ? "Bi-weekly" : "Monthly",
    },
  ];

  async function afterChange() {
    await load();
    onChanged?.();
  }

  return (
    <div>
      {error ? (
        <p className="mb-3 rounded-md border border-clay/30 bg-[#f8ebe6] px-3 py-2 text-sm text-clay">
          {error}
        </p>
      ) : null}
      <DataTable
        rows={rows}
        columns={columns}
        draft={draft}
        onDraftChange={setDraft}
        createLabel="Add category"
        onCreate={async () => {
          await api.post("/api/budget-categories", payloadFrom(draft));
          setDraft(EMPTY);
          await afterChange();
        }}
        onUpdate={async (id, patch) => {
          await api.put(`/api/budget-categories/${id}`, payloadFrom(patch));
          await afterChange();
        }}
        onDelete={async (id) => {
          await api.delete(`/api/budget-categories/${id}`);
          await afterChange();
        }}
      />
    </div>
  );
}
