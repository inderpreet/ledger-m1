"use client";

import { useEffect, useMemo, useState } from "react";
import { accountHex, accountTextClass, accountTone } from "@/lib/accountStyle";
import { api } from "@/lib/api";
import { formatDateWithDay, formatMoney } from "@/lib/format";
import type { Account, CreditCard, StatementCycle, StatementTotal } from "@/lib/types";

export function CreditCardSetup() {
  const [cards, setCards] = useState<CreditCard[]>([]);
  const [banks, setBanks] = useState<Account[]>([]);
  const [cycles, setCycles] = useState<StatementCycle[]>([]);
  const [totals, setTotals] = useState<StatementTotal[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [anchor, setAnchor] = useState({
    statement_from: "",
    statement_to: "",
    payment_due: "",
  });

  async function load(keepId?: number) {
    const [cc, accounts, allCycles, allTotals] = await Promise.all([
      api.get<CreditCard[]>("/api/credit-cards"),
      api.get<Account[]>("/api/accounts"),
      api.get<StatementCycle[]>("/api/statement-cycles"),
      api.get<StatementTotal[]>("/api/cc-statement-totals"),
    ]);
    setCards(cc);
    setBanks(accounts.filter((a) => a.account_type === "bank"));
    setCycles(allCycles);
    setTotals(allTotals);
    setSelectedId((prev) => keepId ?? prev ?? cc[0]?.id ?? null);
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, []);

  const selected = cards.find((c) => c.id === selectedId) ?? null;
  const cardCycles = useMemo(
    () => cycles.filter((c) => c.account_id === selectedId),
    [cycles, selectedId],
  );
  const totalsByCycle = useMemo(
    () => Object.fromEntries(totals.map((t) => [t.cycle_id, t.total])),
    [totals],
  );

  async function changeFunding(funding_account_id: number) {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await api.put(`/api/credit-cards/${selected.id}/funding`, { funding_account_id });
      await load(selected.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function generate() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await api.post(`/api/statement-cycles/${selected.id}/generate`, {});
      await load(selected.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generate failed");
    } finally {
      setBusy(false);
    }
  }

  async function createAnchor() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/statement-cycles", { account_id: selected.id, ...anchor });
      setAnchor({ statement_from: "", statement_to: "", payment_due: "" });
      await load(selected.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveCycle(cycle: StatementCycle, patch: Partial<StatementCycle>) {
    setBusy(true);
    setError(null);
    try {
      await api.put(`/api/statement-cycles/${cycle.id}`, patch);
      await load(selected?.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function deleteCycle(cycle: StatementCycle) {
    if (!confirm(`Delete the ${cycle.statement_from} – ${cycle.statement_to} cycle?`)) return;
    setBusy(true);
    setError(null);
    try {
      await api.delete(`/api/statement-cycles/${cycle.id}`);
      await load(selected?.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function deleteAllCycles() {
    if (!selected) return;
    if (!confirm(`Delete all statement cycles for ${selected.name}?`)) return;
    setBusy(true);
    setError(null);
    try {
      await api.delete(`/api/credit-cards/${selected.id}/statement-cycles`);
      await load(selected.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          {cards.map((card) => (
            <button
              key={card.id}
              className={`rounded-full border px-3 py-1 text-sm ${
                card.id === selectedId ? "text-white" : `bg-card ${accountTextClass(card.name)}`
              }`}
              style={
                card.id === selectedId
                  ? { backgroundColor: accountHex(card.name), borderColor: accountHex(card.name) }
                  : {
                      borderColor:
                        accountTone(card.name) === "neutral" ? undefined : accountHex(card.name),
                    }
              }
              onClick={() => setSelectedId(card.id)}
            >
              {card.name}
            </button>
          ))}
        </div>
        {selected && cardCycles.length > 0 ? (
          <div className="flex flex-wrap items-center gap-2">
            <button
              className="rounded-md bg-moss px-3 py-1.5 text-xs font-medium text-white hover:bg-moss-deep disabled:opacity-50"
              disabled={busy}
              onClick={generate}
            >
              Generate cycles
            </button>
            <button
              className="rounded-md border border-clay/40 px-3 py-1.5 text-xs font-medium text-clay hover:bg-[#f8ebe6] disabled:opacity-50"
              disabled={busy}
              onClick={deleteAllCycles}
            >
              Delete all
            </button>
          </div>
        ) : null}
      </div>
      {error ? (
        <p className="mb-4 rounded-md border border-clay/30 bg-[#f8ebe6] px-3 py-2 text-sm text-clay">
          {error}
        </p>
      ) : null}
      {selected ? (
        <div className="mb-5 flex flex-wrap items-center gap-3 rounded-lg border border-rule bg-card px-4 py-3 text-sm">
          <span className="text-ink/55">Funds from</span>
          <select
            className={`rounded-md border border-rule bg-white px-2 py-1 ${
              selected.funding_account_name ? accountTextClass(selected.funding_account_name) : ""
            }`}
            value={selected.funding_account_id ?? ""}
            disabled={busy}
            onChange={(e) => changeFunding(Number(e.target.value))}
          >
            {banks.map((bank) => (
              <option key={bank.id} value={bank.id} className={accountTextClass(bank.name)}>
                {bank.name}
              </option>
            ))}
          </select>
        </div>
      ) : null}
      {selected && cardCycles.length === 0 ? (
        <div className="rounded-lg border border-dashed border-rule bg-card px-4 py-5">
          <p className="font-medium">No cycles yet</p>
          <p className="mt-1 text-sm text-ink/60">
            Enter a starting statement cycle, then generate the rest through the model end date.
          </p>
          <div className="mt-4 flex flex-wrap items-end gap-3 text-sm">
            <label>
              <span className="mb-1 block text-[11px] uppercase tracking-wider text-ink/45">From</span>
              <input
                type="date"
                className="rounded-md border border-rule bg-white px-2 py-1"
                value={anchor.statement_from}
                onChange={(e) => setAnchor((p) => ({ ...p, statement_from: e.target.value }))}
              />
            </label>
            <label>
              <span className="mb-1 block text-[11px] uppercase tracking-wider text-ink/45">To</span>
              <input
                type="date"
                className="rounded-md border border-rule bg-white px-2 py-1"
                value={anchor.statement_to}
                onChange={(e) => setAnchor((p) => ({ ...p, statement_to: e.target.value }))}
              />
            </label>
            <label>
              <span className="mb-1 block text-[11px] uppercase tracking-wider text-ink/45">Due</span>
              <input
                type="date"
                className="rounded-md border border-rule bg-white px-2 py-1"
                value={anchor.payment_due}
                onChange={(e) => setAnchor((p) => ({ ...p, payment_due: e.target.value }))}
              />
            </label>
            <button
              className="rounded-md bg-moss px-3 py-1.5 text-xs font-medium text-white hover:bg-moss-deep disabled:opacity-50"
              disabled={busy}
              onClick={createAnchor}
            >
              Save starting cycle
            </button>
          </div>
        </div>
      ) : null}
      {selected && cardCycles.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-rule bg-card">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-rule text-[11px] uppercase tracking-wider text-ink/55">
              <tr>
                <th className="px-3 py-2 font-medium">From</th>
                <th className="px-3 py-2 font-medium">To</th>
                <th className="px-3 py-2 font-medium">Payment due</th>
                <th className="px-3 py-2 font-medium">Due amount</th>
                <th className="px-3 py-2 font-medium">Source</th>
                <th className="px-3 py-2 font-medium"> </th>
              </tr>
            </thead>
            <tbody>
              {cardCycles.map((cycle) => (
                <CycleRow
                  key={cycle.id}
                  cycle={cycle}
                  total={totalsByCycle[cycle.id]}
                  busy={busy}
                  onSave={saveCycle}
                  onDelete={deleteCycle}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

function CycleRow({
  cycle,
  total,
  busy,
  onSave,
  onDelete,
}: {
  cycle: StatementCycle;
  total: number | undefined;
  busy: boolean;
  onSave: (cycle: StatementCycle, patch: Partial<StatementCycle>) => Promise<void>;
  onDelete: (cycle: StatementCycle) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [from, setFrom] = useState(cycle.statement_from);
  const [to, setTo] = useState(cycle.statement_to);
  const [due, setDue] = useState(cycle.payment_due);

  useEffect(() => {
    setFrom(cycle.statement_from);
    setTo(cycle.statement_to);
    setDue(cycle.payment_due);
  }, [cycle]);

  return (
    <tr className="border-b border-rule/70 last:border-0">
      <td className="px-3 py-2">
        {editing ? (
          <input
            type="date"
            className="rounded-md border border-rule px-2 py-1"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
          />
        ) : (
          formatDateWithDay(cycle.statement_from)
        )}
      </td>
      <td className="px-3 py-2">
        {editing ? (
          <input
            type="date"
            className="rounded-md border border-rule px-2 py-1"
            value={to}
            onChange={(e) => setTo(e.target.value)}
          />
        ) : (
          formatDateWithDay(cycle.statement_to)
        )}
      </td>
      <td className="px-3 py-2">
        {editing ? (
          <input
            type="date"
            className="rounded-md border border-rule px-2 py-1"
            value={due}
            onChange={(e) => setDue(e.target.value)}
          />
        ) : (
          formatDateWithDay(cycle.payment_due)
        )}
      </td>
      <td className="px-3 py-2 tabular">{total === undefined ? "—" : formatMoney(total)}</td>
      <td className="px-3 py-2 text-ink/55">{cycle.is_generated ? "generated" : "edited"}</td>
      <td className="px-3 py-2 text-right">
        {editing ? (
          <>
            <button
              className="text-moss hover:underline disabled:opacity-50"
              disabled={busy}
              onClick={async () => {
                await onSave(cycle, {
                  statement_from: from,
                  statement_to: to,
                  payment_due: due,
                });
                setEditing(false);
              }}
            >
              Save
            </button>
            <button className="ml-3 text-ink/50 hover:underline" onClick={() => setEditing(false)}>
              Cancel
            </button>
          </>
        ) : (
          <>
            <button className="text-ink/70 hover:underline" onClick={() => setEditing(true)}>
              Edit
            </button>
            <button
              className="ml-3 text-clay hover:underline disabled:opacity-50"
              disabled={busy}
              onClick={() => onDelete(cycle)}
            >
              Delete
            </button>
          </>
        )}
      </td>
    </tr>
  );
}
