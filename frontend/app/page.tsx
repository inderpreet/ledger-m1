"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AccountName } from "@/components/AccountName";
import { BalanceChart } from "@/components/BalanceChart";
import { ExpensePie } from "@/components/ExpensePie";
import { LowBalanceBanner } from "@/components/LowBalanceBanner";
import { PageHeader } from "@/components/PageHeader";
import { accountHex, accountTextClass } from "@/lib/accountStyle";
import { api } from "@/lib/api";
import { daysUntil, formatMoney } from "@/lib/format";
import type { CashflowPayload, DashboardPayload, Settings } from "@/lib/types";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [cashflow, setCashflow] = useState<CashflowPayload | null>(null);
  const [threshold, setThreshold] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function load() {
    const [dash, flow] = await Promise.all([
      api.get<DashboardPayload>("/api/dashboard"),
      api.get<CashflowPayload>("/api/daily-cashflow"),
    ]);
    setData(dash);
    setCashflow(flow);
    setThreshold(String(dash.threshold));
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, []);

  async function saveThreshold() {
    setSaving(true);
    setError(null);
    try {
      await api.put<Settings>("/api/settings", { low_balance_threshold: Number(threshold) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (!data && !error) {
    return <p className="text-sm text-ink/50">Loading dashboard…</p>;
  }

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle={data ? `Projected from ${data.as_of} through ${data.model_end_date}` : undefined}
        action={
          <label className="flex items-center gap-2 text-sm">
            <span className="text-ink/60">Threshold</span>
            <input
              className="w-28 rounded-md border border-rule bg-card px-2 py-1 tabular"
              type="number"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
            />
            <button
              className="rounded-md bg-moss px-3 py-1.5 text-xs font-medium text-white hover:bg-moss-deep disabled:opacity-50"
              disabled={saving}
              onClick={saveThreshold}
            >
              Save
            </button>
          </label>
        }
      />
      {error ? (
        <p className="mb-4 rounded-md border border-clay/30 bg-[#f8ebe6] px-3 py-2 text-sm text-clay">
          {error}
        </p>
      ) : null}
      {data && !data.opening_balances_set ? (
        <div className="mb-6 rounded-lg border border-rule bg-card px-4 py-3 text-sm">
          Opening balances are not set yet. Projections treat them as $0 until you enter them in{" "}
          <Link href="/setup" className="text-moss underline">
            Setup
          </Link>
          .
        </div>
      ) : null}
      {data ? <LowBalanceBanner data={data} /> : null}
      {data ? (
        <div className="grid gap-4 md:grid-cols-3">
          {data.accounts.map((account) => (
            <BalanceCard
              key={account.id}
              name={account.name}
              balance={account.current_balance}
              lowDate={account.first_low_balance_date}
              threshold={data.threshold}
            />
          ))}
          <BalanceCard
            name="Combined"
            balance={data.combined.current_balance}
            lowDate={data.combined.first_low_balance_date}
            threshold={data.threshold}
            muted
          />
        </div>
      ) : null}
      {cashflow || data?.expenses_by_category ? (
        <div className="mt-6 grid gap-6 lg:grid-cols-3">
          {cashflow ? (
            <section className="lg:col-span-2">
              <div className="mb-3 flex items-end justify-between gap-3">
                <h2 className="font-serif text-xl tracking-tight">Bank account flow</h2>
                <Link href="/bank-flow" className="text-sm text-moss hover:underline">
                  Open full table
                </Link>
              </div>
              <BalanceChart data={cashflow} />
            </section>
          ) : null}
          {data ? (
            <section>
              <h2 className="mb-3 font-serif text-xl tracking-tight">Expenses by category</h2>
              <ExpensePie rows={data.expenses_by_category ?? []} />
            </section>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function BalanceCard({
  name,
  balance,
  lowDate,
  threshold,
  muted,
}: {
  name: string;
  balance: number | null;
  lowDate: string | null;
  threshold: number;
  muted?: boolean;
}) {
  const days = daysUntil(lowDate);
  const urgent = days !== null && days <= 30;
  return (
    <article
      className={`rounded-lg border px-5 py-4 ${
        muted ? "border-dashed border-rule bg-transparent" : "border-rule bg-card"
      }`}
      style={muted ? undefined : { borderLeftColor: accountHex(name), borderLeftWidth: 4 }}
    >
      <p
        className={`text-[11px] uppercase tracking-[0.16em] ${
          muted ? "text-ink/50" : accountTextClass(name)
        }`}
      >
        <AccountName name={name} />
      </p>
      <p
        className={`mt-2 font-serif text-3xl tabular tracking-tight ${
          muted ? "" : accountTextClass(name)
        }`}
        style={muted ? undefined : { color: accountHex(name) }}
      >
        {formatMoney(balance)}
      </p>
      <p className={`mt-3 text-sm ${urgent ? "text-clay" : "text-ink/55"}`}>
        {lowDate
          ? `Below ${formatMoney(threshold)} on ${lowDate}${days !== null ? ` (${days}d)` : ""}`
          : `Stays above ${formatMoney(threshold)} in this window`}
      </p>
    </article>
  );
}
