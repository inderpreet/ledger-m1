"use client";

import { useEffect, useMemo, useState } from "react";
import { DataTable, type Column } from "@/components/DataTable";
import { api } from "@/lib/api";
import { calculatedBudgetFromItems } from "@/lib/budgetCompare";
import type { BudgetCategory } from "@/lib/categories";
import { formatMoney } from "@/lib/format";
import type { RecurringItem } from "@/lib/types";

const EMPTY: Record<string, string | number | boolean | null> = {
  name: "",
  amount: "",
  period: "monthly",
};

type BudgetRow = BudgetCategory & { calculated: number };

function payloadFrom(record: Record<string, unknown>) {
  const amountRaw = record.amount;
  return {
    name: String(record.name ?? "").trim(),
    amount: amountRaw === "" || amountRaw === null || amountRaw === undefined ? null : Number(amountRaw),
    period: String(record.period || "monthly"),
  };
}

function periodLabel(period: string): string {
  if (period === "yearly") return "Yearly";
  if (period === "biweekly") return "Bi-weekly";
  return "Monthly";
}

export function BudgetTable({
  refreshKey = 0,
  onChanged,
}: {
  refreshKey?: number;
  onChanged?: () => void;
}) {
  const [categories, setCategories] = useState<BudgetCategory[]>([]);
  const [items, setItems] = useState<RecurringItem[]>([]);
  const [draft, setDraft] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [cats, recurring] = await Promise.all([
      api.get<BudgetCategory[]>("/api/budget-categories"),
      api.get<RecurringItem[]>("/api/recurring-items"),
    ]);
    setCategories(cats);
    setItems(recurring);
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [refreshKey]);

  const rows: BudgetRow[] = useMemo(
    () =>
      categories.map((category) => {
        const inCategory = items.filter((item) => item.category === category.name);
        return { ...category, calculated: calculatedBudgetFromItems(inCategory, category) };
      }),
    [categories, items],
  );

  const columns: Column<BudgetRow>[] = [
    { key: "name", label: "Category" },
    {
      key: "period",
      label: "Period",
      type: "select",
      options: [
        { value: "monthly", label: "Monthly" },
        { value: "biweekly", label: "Bi-weekly" },
        { value: "yearly", label: "Yearly" },
      ],
      render: (row) => periodLabel(row.period),
    },
    {
      key: "amount",
      label: "Amount",
      type: "number",
      render: (row) => <span className="tabular">{formatMoney(row.amount)}</span>,
    },
    {
      key: "calculated",
      label: "Calculated",
      editable: false,
      render: (row) => <CalculatedCell row={row} />,
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

function CalculatedCell({ row }: { row: BudgetRow }) {
  if (typeof row.calculated !== "number" || !row.id) {
    return <span className="text-ink/35">—</span>;
  }
  const calculatedLabel = formatMoney(row.calculated);
  if (row.amount == null) {
    return <span className="tabular text-ink/55">{calculatedLabel}</span>;
  }
  const delta = row.amount - row.calculated;
  const over = delta < -0.005;
  const under = delta > 0.005;
  const tone = over ? "text-clay" : under ? "text-moss" : "text-ink/55";
  const vs =
    over ? `${formatMoney(Math.abs(delta))} over` : under ? `${formatMoney(delta)} under` : "on budget";
  return (
    <span className={`tabular ${tone}`}>
      {calculatedLabel}
      <span className="ml-2 text-xs">{vs}</span>
    </span>
  );
}
