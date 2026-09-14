"use client";

import { useEffect, useState } from "react";
import { AccountName } from "@/components/AccountName";
import { CreditCardSetup } from "@/components/CreditCardSetup";
import { DatabaseBackup } from "@/components/DatabaseBackup";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { Account, Settings } from "@/lib/types";

export default function SetupPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [banks, setBanks] = useState<Account[]>([]);
  const [threshold, setThreshold] = useState("");
  const [endDate, setEndDate] = useState("");
  const [balances, setBalances] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dataEpoch, setDataEpoch] = useState(0);

  async function load() {
    const [s, accounts] = await Promise.all([
      api.get<Settings>("/api/settings"),
      api.get<Account[]>("/api/accounts"),
    ]);
    const bankAccounts = accounts.filter((a) => a.account_type === "bank");
    setSettings(s);
    setBanks(bankAccounts);
    setThreshold(String(s.low_balance_threshold));
    setEndDate(s.model_end_date);
    setBalances(
      Object.fromEntries(
        bankAccounts.map((a) => [a.id, a.opening_balance === null ? "" : String(a.opening_balance)]),
      ),
    );
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, []);

  async function save() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.put("/api/settings", {
        low_balance_threshold: Number(threshold),
        model_end_date: endDate,
      });
      for (const bank of banks) {
        const raw = balances[bank.id];
        if (raw === "") continue;
        await api.put(`/api/accounts/${bank.id}`, { opening_balance: Number(raw) });
      }
      await load();
      setMessage("Saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Setup"
        subtitle="Opening balances, projection window, and credit-card statement cycles."
      />
      {error ? (
        <p className="mb-4 rounded-md border border-clay/30 bg-[#f8ebe6] px-3 py-2 text-sm text-clay">
          {error}
        </p>
      ) : null}
      {message ? <p className="mb-4 text-sm text-moss">{message}</p> : null}

      <section className="mb-10 max-w-xl">
        <h2 className="mb-3 font-serif text-xl tracking-tight">Accounts & model</h2>
        {!settings ? (
          <p className="text-sm text-ink/50">Loading…</p>
        ) : (
          <div className="space-y-5 rounded-lg border border-rule bg-card p-5">
            <label className="block text-sm">
              <span className="mb-1 block text-[11px] uppercase tracking-wider text-ink/45">
                Low-balance threshold
              </span>
              <input
                type="number"
                className="w-full rounded-md border border-rule bg-white px-3 py-2 tabular"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-[11px] uppercase tracking-wider text-ink/45">
                Model end date
              </span>
              <input
                type="date"
                className="w-full rounded-md border border-rule bg-white px-3 py-2"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </label>
            <div>
              <p className="mb-2 text-[11px] uppercase tracking-wider text-ink/45">
                Opening balances
              </p>
              <div className="space-y-3">
                {banks.map((bank) => (
                  <label key={bank.id} className="block text-sm">
                    <span className="mb-1 block">
                      <AccountName name={bank.name} />
                    </span>
                    <input
                      type="number"
                      step="0.01"
                      placeholder="Enter current balance"
                      className="w-full rounded-md border border-rule bg-white px-3 py-2 tabular"
                      value={balances[bank.id] ?? ""}
                      onChange={(e) =>
                        setBalances((prev) => ({ ...prev, [bank.id]: e.target.value }))
                      }
                    />
                    {bank.opening_balance_date ? (
                      <span className="mt-1 block text-xs text-ink/45">
                        Confirmed {bank.opening_balance_date}
                      </span>
                    ) : null}
                  </label>
                ))}
              </div>
            </div>
            <button
              className="rounded-md bg-moss px-4 py-2 text-sm font-medium text-white hover:bg-moss-deep disabled:opacity-50"
              disabled={busy}
              onClick={save}
            >
              Save setup
            </button>
          </div>
        )}
      </section>

      <DatabaseBackup
        onImported={async () => {
          await load();
          setDataEpoch((n) => n + 1);
        }}
      />

      <section>
        <h2 className="mb-3 font-serif text-xl tracking-tight">Credit cards</h2>
        <p className="mb-4 text-sm text-ink/55">
          Charges stay on the card until the funding account is debited on payment due.
        </p>
        <CreditCardSetup key={dataEpoch} />
      </section>
    </div>
  );
}
