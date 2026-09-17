"use client";

import { useEffect, useMemo, useState } from "react";
import { AccountName } from "@/components/AccountName";
import { DataTable, type Column } from "@/components/DataTable";
import { api } from "@/lib/api";
import { groupRecurringByCategory } from "@/lib/budgetCompare";
import { formatBiweeklyWhen, formatMoney } from "@/lib/format";
import type { Account, RecurringItem } from "@/lib/types";
import { categorySelectOptions, type BudgetCategory } from "@/lib/categories";

const EMPTY: Record<string, string | number | boolean | null> = {
  description: "",
  item_type: "expense",
  amount: "",
  day_of_month: "",
  start_date: "",
  end_date: "",
  target_account_id: "",
  category: "",
  active: true,
  term: "monthly",
};

export function RecurringTable({ onChanged }: { onChanged?: () => void }) {
  const [rows, setRows] = useState<RecurringItem[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<BudgetCategory[]>([]);
  const [draft, setDraft] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [items, accts, cats] = await Promise.all([
      api.get<RecurringItem[]>("/api/recurring-items"),
      api.get<Account[]>("/api/accounts"),
      api.get<BudgetCategory[]>("/api/budget-categories"),
    ]);
    setRows(items);
    setAccounts(accts);
    setCategories(cats);
    if (!draft.target_account_id && accts[0]) {
      setDraft((prev) => ({ ...prev, target_account_id: String(accts[0].id) }));
    }
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const accountOptions = accounts.map((a) => ({ value: String(a.id), label: a.name }));
  const byId = useMemo(() => Object.fromEntries(accounts.map((a) => [a.id, a.name])), [accounts]);
  const groups = useMemo(() => groupRecurringByCategory(rows, categories), [rows, categories]);

  const columns: Column<RecurringItem>[] = [
    { key: "description", label: "Description" },
    {
      key: "item_type",
      label: "Type",
      type: "select",
      options: [
        { value: "income", label: "income" },
        { value: "expense", label: "expense" },
      ],
    },
    {
      key: "amount",
      label: "Amount",
      type: "number",
      render: (row) => <span className="tabular">{formatMoney(row.amount)}</span>,
    },
    {
      key: "term",
      label: "Term",
      type: "select",
      options: [
        { value: "monthly", label: "Monthly" },
        { value: "biweekly", label: "Bi-weekly" },
      ],
      render: (row) => (row.term === "biweekly" ? "Bi-weekly" : "Monthly"),
    },
    {
      key: "day_of_month",
      label: "When",
      type: "number",
      editable: (values) => values.term !== "biweekly",
      render: (row) =>
        row.term === "biweekly" ? (
          <span className="tabular text-xs">{formatBiweeklyWhen(row.start_date)}</span>
        ) : (
          <span className="tabular">{row.day_of_month ?? "—"}</span>
        ),
    },
    { key: "start_date", label: "Start", type: "date" },
    { key: "end_date", label: "End", type: "date" },
    {
      key: "target_account_id",
      label: "Account",
      type: "select",
      options: accountOptions,
      render: (row) => (
        <AccountName name={String(byId[row.target_account_id] ?? row.target_account_id)} />
      ),
    },
    { key: "category", label: "Category", type: "select", options: categorySelectOptions(categories, rows.map((r) => r.category)) },
    {
      key: "active",
      label: "Active",
      type: "checkbox",
      render: (row) => (row.active ? "yes" : "no"),
    },
  ];

  function payloadFrom(record: Record<string, unknown>) {
    const amountRaw = record.amount;
    const dayRaw = record.day_of_month;
    const term = String(record.term || "monthly");
    return {
      description: String(record.description ?? ""),
      item_type: record.item_type,
      amount: amountRaw === "" || amountRaw === null ? null : Number(amountRaw),
      day_of_month:
        term === "biweekly" || dayRaw === "" || dayRaw === null ? null : Number(dayRaw),
      start_date: record.start_date || null,
      end_date: record.end_date || null,
      target_account_id: Number(record.target_account_id),
      category: record.category || null,
      active: Boolean(record.active),
      term,
    };
  }

  return (
    <div>
      {error ? (
        <p className="mb-3 rounded-md border border-clay/30 bg-[#f8ebe6] px-3 py-2 text-sm text-clay">
          {error}
        </p>
      ) : null}
      {groups.map((group) => (
        <section key={group.key} className="mb-8">
          <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
            <h3 className="font-serif text-lg tracking-tight">{group.name}</h3>
            <BudgetCompareLine income={group.income} spent={group.spent} />
          </div>
          {group.items.length > 0 ? (
            <DataTable
              rows={group.items}
              columns={columns}
              draft={draft}
              onDraftChange={setDraft}
              showCreate={false}
              onUpdate={async (id, patch) => {
                await api.put(`/api/recurring-items/${id}`, payloadFrom({ ...patch }));
                await load();
                onChanged?.();
              }}
              onDelete={async (id) => {
                await api.delete(`/api/recurring-items/${id}`);
                await load();
                onChanged?.();
              }}
            />
          ) : (
            <p className="rounded-lg border border-rule bg-card px-3 py-2 text-sm text-ink/50">
              No recurring items in this category yet.
            </p>
          )}
        </section>
      ))}
      <section>
        <h3 className="mb-3 font-serif text-lg tracking-tight">Add recurring</h3>
        <DataTable
          rows={[]}
          columns={columns}
          draft={draft}
          onDraftChange={setDraft}
          createLabel="Add recurring"
          onCreate={async () => {
            await api.post("/api/recurring-items", payloadFrom(draft));
            setDraft({ ...EMPTY, target_account_id: draft.target_account_id });
            await load();
            onChanged?.();
          }}
          onUpdate={async () => undefined}
          onDelete={async () => undefined}
        />
      </section>
    </div>
  );
}

function BudgetCompareLine({ income, spent }: { income: number; spent: number }) {
  const incomeOnly = income > 0.005 && spent < 0.005;
  const mixed =
    income > 0.005 && spent > 0.005
      ? `Income ${formatMoney(income)} / mo · expenses ${formatMoney(spent)} / mo`
      : incomeOnly
        ? `Recurring income ${formatMoney(income)} / mo`
        : `Recurring ${formatMoney(spent)} / mo`;
  return <span className="text-sm tabular text-ink/55">{mixed}</span>;
}
