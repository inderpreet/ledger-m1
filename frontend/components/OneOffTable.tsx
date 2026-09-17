"use client";

import { useEffect, useMemo, useState } from "react";
import { AccountName } from "@/components/AccountName";
import { DataTable, type Column } from "@/components/DataTable";
import { api } from "@/lib/api";
import { formatMoney, isoToday } from "@/lib/format";
import type { Account, OneOffItem } from "@/lib/types";
import { categorySelectOptions, type BudgetCategory } from "@/lib/categories";

const EMPTY: Record<string, string | number | boolean | null> = {
  description: "",
  item_type: "expense",
  amount: "",
  item_date: isoToday(),
  target_account_id: "",
  category: "",
};

export function OneOffTable() {
  const [rows, setRows] = useState<OneOffItem[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<BudgetCategory[]>([]);
  const [draft, setDraft] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [items, accts, cats] = await Promise.all([
      api.get<OneOffItem[]>("/api/one-off-items"),
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

  const columns: Column<OneOffItem>[] = [
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
    { key: "item_date", label: "Date", type: "date" },
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
  ];

  function payloadFrom(record: Record<string, unknown>) {
    return {
      description: String(record.description ?? ""),
      item_type: record.item_type,
      amount: Number(record.amount),
      item_date: record.item_date,
      target_account_id: Number(record.target_account_id),
      category: record.category || null,
    };
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
        createLabel="Add one-off"
        onCreate={async () => {
          await api.post("/api/one-off-items", payloadFrom(draft));
          setDraft({ ...EMPTY, target_account_id: draft.target_account_id, item_date: isoToday() });
          await load();
        }}
        onUpdate={async (id, patch) => {
          await api.put(`/api/one-off-items/${id}`, payloadFrom(patch));
          await load();
        }}
        onDelete={async (id) => {
          await api.delete(`/api/one-off-items/${id}`);
          await load();
        }}
      />
    </div>
  );
}
