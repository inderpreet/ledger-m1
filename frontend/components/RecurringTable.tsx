"use client";

import { useEffect, useMemo, useState } from "react";
import { AccountName } from "@/components/AccountName";
import { DataTable, type Column } from "@/components/DataTable";
import { api } from "@/lib/api";
import { formatBiweeklyWhen, formatMoney } from "@/lib/format";
import type { Account, RecurringItem } from "@/lib/types";

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

export function RecurringTable() {
  const [rows, setRows] = useState<RecurringItem[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [draft, setDraft] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [items, accts] = await Promise.all([
      api.get<RecurringItem[]>("/api/recurring-items"),
      api.get<Account[]>("/api/accounts"),
    ]);
    setRows(items);
    setAccounts(accts);
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
    { key: "category", label: "Category" },
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
      <DataTable
        rows={rows}
        columns={columns}
        draft={draft}
        onDraftChange={setDraft}
        createLabel="Add recurring"
        onCreate={async () => {
          await api.post("/api/recurring-items", payloadFrom(draft));
          setDraft({ ...EMPTY, target_account_id: draft.target_account_id });
          await load();
        }}
        onUpdate={async (id, patch) => {
          await api.put(`/api/recurring-items/${id}`, payloadFrom({ ...patch }));
          await load();
        }}
        onDelete={async (id) => {
          await api.delete(`/api/recurring-items/${id}`);
          await load();
        }}
      />
    </div>
  );
}
