"use client";

import { useRef, useState, type ChangeEvent } from "react";
import { downloadDatabase, uploadDatabase } from "@/lib/api";

type Imported = Record<string, number>;

export function DatabaseBackup({ onImported }: { onImported: () => Promise<void> | void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [busy, setBusy] = useState<"download" | "upload" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function summarize(imported: Imported): string {
    const bits = [
      `${imported.accounts ?? 0} accounts`,
      `${imported.recurring_items ?? 0} recurring`,
      `${imported.one_off_items ?? 0} one-off`,
      `${imported.statement_cycles ?? 0} cycles`,
    ];
    return `Imported ${bits.join(", ")}. Login on this server was kept.`;
  }

  async function download() {
    setBusy("download");
    setError(null);
    setMessage(null);
    try {
      await downloadDatabase();
      setMessage("Download started.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setBusy(null);
    }
  }

  function chooseFile() {
    setError(null);
    setMessage(null);
    inputRef.current?.click();
  }

  function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    event.target.value = "";
    setPendingFile(file);
  }

  async function confirmUpload() {
    if (!pendingFile) return;
    setBusy("upload");
    setError(null);
    setMessage(null);
    try {
      const result = await uploadDatabase(pendingFile);
      setPendingFile(null);
      setMessage(summarize(result.imported));
      await onImported();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="mb-10 max-w-xl">
      <h2 className="mb-3 font-serif text-xl tracking-tight">Data</h2>
      <p className="mb-4 text-sm text-ink/55">
        Download a copy of this server&apos;s SQLite file, or replace accounts, expenses, cards, and
        settings from a file you already use locally. The login on this server stays the same.
      </p>
      {error ? (
        <p className="mb-4 rounded-md border border-clay/30 bg-[#f8ebe6] px-3 py-2 text-sm text-clay">
          {error}
        </p>
      ) : null}
      {message ? <p className="mb-4 text-sm text-moss">{message}</p> : null}

      <div className="space-y-4 rounded-lg border border-rule bg-card p-5">
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            className="rounded-md border border-rule bg-white px-4 py-2 text-sm font-medium hover:bg-paper disabled:opacity-50"
            disabled={busy !== null}
            onClick={download}
          >
            {busy === "download" ? "Downloading…" : "Download data"}
          </button>
          <button
            type="button"
            className="rounded-md bg-moss px-4 py-2 text-sm font-medium text-white hover:bg-moss-deep disabled:opacity-50"
            disabled={busy !== null}
            onClick={chooseFile}
          >
            Upload database
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".db,.sqlite,.sqlite3,application/vnd.sqlite3,application/octet-stream"
            className="hidden"
            onChange={onFile}
          />
        </div>

        {pendingFile ? (
          <div className="rounded-md border border-clay/30 bg-[#f8ebe6] p-4">
            <p className="text-sm text-ink">
              Replace all ledger data on this server with{" "}
              <span className="font-medium">{pendingFile.name}</span>? This cannot be undone.
            </p>
            <p className="mt-2 text-xs text-ink/55">
              Opening balances, expenses, cards, and settings will be overwritten. Your username and
              password will not change.
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="button"
                className="rounded-md bg-clay px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                disabled={busy !== null}
                onClick={confirmUpload}
              >
                {busy === "upload" ? "Replacing…" : "Replace data"}
              </button>
              <button
                type="button"
                className="rounded-md border border-rule bg-white px-4 py-2 text-sm disabled:opacity-50"
                disabled={busy !== null}
                onClick={() => setPendingFile(null)}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
