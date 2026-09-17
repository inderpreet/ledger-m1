"use client";

import { useEffect, useState } from "react";
import { BalanceChart } from "@/components/BalanceChart";
import { PageHeader } from "@/components/PageHeader";
import { accountTextClass } from "@/lib/accountStyle";
import { api } from "@/lib/api";
import { formatDateWithDay, formatMoney } from "@/lib/format";
import type { CashflowMovement, CashflowPayload, Settings } from "@/lib/types";

export function CashflowView({
  title,
  subtitle,
  endpoint,
}: {
  title: string;
  subtitle: string;
  endpoint: string;
}) {
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [data, setData] = useState<CashflowPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load(nextStart = start, nextEnd = end) {
    const payload = await api.get<CashflowPayload>(
      `${endpoint}?start=${nextStart}&end=${nextEnd}`,
    );
    setData(payload);
  }

  useEffect(() => {
    api
      .get<Settings>("/api/settings")
      .then((settings) => {
        setStart(settings.model_start_date);
        setEnd(settings.model_end_date);
        return load(settings.model_start_date, settings.model_end_date);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint]);

  return (
    <div>
      <PageHeader
        title={title}
        subtitle={subtitle}
        action={
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <input
              className="rounded-md border border-rule bg-card px-2 py-1"
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
            <span className="text-ink/40">to</span>
            <input
              className="rounded-md border border-rule bg-card px-2 py-1"
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
            <button
              className="rounded-md bg-moss px-3 py-1.5 text-xs font-medium text-white hover:bg-moss-deep"
              onClick={() =>
                load().catch((err) => setError(err instanceof Error ? err.message : "Failed"))
              }
            >
              Apply
            </button>
          </div>
        }
      />
      {error ? (
        <p className="mb-4 rounded-md border border-clay/30 bg-[#f8ebe6] px-3 py-2 text-sm text-clay">
          {error}
        </p>
      ) : null}
      {data ? <BalanceChart data={data} /> : null}
      {data ? (
        <div className="mt-6 overflow-x-auto rounded-lg border border-rule bg-card">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-rule text-[11px] uppercase tracking-wider text-ink/55">
              <tr>
                <th className="px-3 py-2 font-medium">Date</th>
                <th className="px-3 py-2 font-medium">Activity</th>
                {data.accounts.map((account) => (
                  <th key={account.id} className={`px-3 py-2 font-medium ${accountTextClass(account.name)}`}>
                    {account.name}
                  </th>
                ))}
                <th className="px-3 py-2 font-medium">Combined</th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row) => {
                const movements = (row.movements ?? []) as CashflowMovement[];
                return (
                  <tr key={String(row.date)} className="border-b border-rule/70 last:border-0 align-top">
                    <td className="px-3 py-1.5 tabular whitespace-nowrap">
                      {formatDateWithDay(String(row.date))}
                    </td>
                    <td className="px-3 py-1.5">
                      {movements.length === 0 ? (
                        <span className="text-ink/30">—</span>
                      ) : (
                        <ul className="space-y-0.5">
                          {movements.map((m, i) => (
                            <li
                              key={`${m.account_id}-${m.description}-${i}`}
                              className={accountTextClass(m.account_name)}
                            >
                              <span className="tabular font-medium">
                                {m.amount > 0 ? "+" : "−"}
                                {formatMoney(Math.abs(m.amount))}
                              </span>
                              <span className="mx-1.5 text-ink/35">·</span>
                              <span>{m.description}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </td>
                    {data.accounts.map((account) => (
                      <td
                        key={account.id}
                        className={`px-3 py-1.5 tabular whitespace-nowrap ${accountTextClass(account.name)}`}
                      >
                        {formatMoney(Number(row[String(account.id)]))}
                      </td>
                    ))}
                    <td className="px-3 py-1.5 tabular whitespace-nowrap">
                      {formatMoney(Number(row.combined))}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-ink/50">Loading cashflow…</p>
      )}
    </div>
  );
}
