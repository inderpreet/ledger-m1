"use client";

import { useState } from "react";

export type Column<T> = {
  key: string;
  label: string;
  type?: "text" | "number" | "date" | "select" | "checkbox";
  options?: { value: string; label: string }[];
  editable?: boolean | ((values: Record<string, unknown>) => boolean);
  width?: string;
  render?: (row: T) => React.ReactNode;
};

type Props<T extends { id: number }> = {
  rows: T[];
  columns: Column<T>[];
  draft: Record<string, string | number | boolean | null>;
  onDraftChange: (next: Record<string, string | number | boolean | null>) => void;
  onCreate?: () => Promise<void> | void;
  onUpdate: (id: number, patch: Record<string, unknown>) => Promise<void> | void;
  onDelete: (id: number) => Promise<void> | void;
  createLabel?: string;
  showCreate?: boolean;
};

function isEditable<T>(col: Column<T>, values: Record<string, unknown>): boolean {
  if (typeof col.editable === "function") return col.editable(values);
  return col.editable !== false;
}

function cellValue(row: Record<string, unknown>, key: string): string {
  const value = row[key];
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

export function DataTable<T extends { id: number }>({
  rows,
  columns,
  draft,
  onDraftChange,
  onCreate,
  onUpdate,
  onDelete,
  createLabel = "Add row",
  showCreate = true,
}: Props<T>) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [edit, setEdit] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function startEdit(row: T) {
    const next: Record<string, string> = {};
    for (const col of columns) {
      next[col.key] = cellValue(row as Record<string, unknown>, col.key);
    }
    setEditingId(row.id);
    setEdit(next);
    setError(null);
  }

  function parseField(col: Column<T>, raw: string): unknown {
    if (col.type === "number") {
      if (raw === "") return null;
      return Number(raw);
    }
    if (col.type === "checkbox") return raw === "true";
    if (raw === "") return null;
    return raw;
  }

  async function save(id: number) {
    setBusy(true);
    setError(null);
    try {
      const patch: Record<string, unknown> = {};
      for (const col of columns) {
        if (!isEditable(col, { ...edit })) continue;
        patch[col.key] = parseField(col, edit[col.key] ?? "");
      }
      await onUpdate(id, patch);
      setEditingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function create() {
    if (!onCreate) return;
    setBusy(true);
    setError(null);
    try {
      await onCreate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    if (!confirm("Delete this row?")) return;
    setBusy(true);
    setError(null);
    try {
      await onDelete(id);
      if (editingId === id) setEditingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      {error ? (
        <p className="mb-3 rounded-md border border-clay/30 bg-[#f8ebe6] px-3 py-2 text-sm text-clay">
          {error}
        </p>
      ) : null}
      <div className="overflow-x-auto rounded-lg border border-rule bg-card">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-rule text-[11px] uppercase tracking-wider text-ink/55">
            <tr>
              {columns.map((col) => (
                <th key={col.key} className="px-3 py-2 font-medium" style={{ width: col.width }}>
                  {col.label}
                </th>
              ))}
              <th className="px-3 py-2 font-medium"> </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const isEditing = editingId === row.id;
              const values = { ...(row as Record<string, unknown>), ...edit };
              return (
                <tr key={row.id} className="border-b border-rule/70 last:border-0">
                  {columns.map((col) => (
                    <td key={col.key} className="px-3 py-2 align-middle">
                      {isEditing && isEditable(col, values) ? (
                        <Field
                          column={col}
                          value={edit[col.key] ?? ""}
                          onChange={(value) => setEdit((prev) => ({ ...prev, [col.key]: value }))}
                        />
                      ) : col.render ? (
                        col.render(isEditing ? ({ ...row, ...edit } as T) : row)
                      ) : (
                        <span className={col.type === "number" ? "tabular" : undefined}>
                          {cellValue(row as Record<string, unknown>, col.key) || "—"}
                        </span>
                      )}
                    </td>
                  ))}
                  <td className="px-3 py-2 whitespace-nowrap text-right">
                    {isEditing ? (
                      <>
                        <button
                          className="text-moss hover:underline disabled:opacity-50"
                          disabled={busy}
                          onClick={() => save(row.id)}
                        >
                          Save
                        </button>
                        <button
                          className="ml-3 text-ink/50 hover:underline"
                          onClick={() => setEditingId(null)}
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <>
                        <button className="text-ink/70 hover:underline" onClick={() => startEdit(row)}>
                          Edit
                        </button>
                        <button
                          className="ml-3 text-clay hover:underline disabled:opacity-50"
                          disabled={busy}
                          onClick={() => remove(row.id)}
                        >
                          Delete
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
            {showCreate ? (
            <tr className="bg-[#f6f1e6]">
              {columns.map((col) => (
                <td key={col.key} className="px-3 py-2">
                  {!isEditable(col, draft) ? (
                    col.render ? (
                      col.render({ ...draft, id: 0 } as T)
                    ) : (
                      <span className="text-ink/35">—</span>
                    )
                  ) : (
                    <Field
                      column={col}
                      value={
                        draft[col.key] === null || draft[col.key] === undefined
                          ? ""
                          : String(draft[col.key])
                      }
                      onChange={(value) => {
                        let next: string | number | boolean | null = value;
                        if (col.type === "checkbox") next = value === "true";
                        onDraftChange({ ...draft, [col.key]: next });
                      }}
                    />
                  )}
                </td>
              ))}
              <td className="px-3 py-2 text-right">
                <button
                  className="rounded-md bg-moss px-3 py-1.5 text-xs font-medium text-white hover:bg-moss-deep disabled:opacity-50"
                  disabled={busy}
                  onClick={create}
                >
                  {createLabel}
                </button>
              </td>
            </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Field<T>({
  column,
  value,
  onChange,
}: {
  column: Column<T>;
  value: string;
  onChange: (value: string) => void;
}) {
  const cls =
    "w-full rounded-md border border-rule bg-white px-2 py-1 text-sm text-ink outline-none focus:border-moss";
  if (column.type === "select") {
    return (
      <select className={cls} value={value} onChange={(e) => onChange(e.target.value)}>
        {(column.options ?? []).map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    );
  }
  if (column.type === "checkbox") {
    return (
      <input
        type="checkbox"
        checked={value === "true"}
        onChange={(e) => onChange(e.target.checked ? "true" : "false")}
      />
    );
  }
  return (
    <input
      className={cls}
      type={column.type === "number" ? "number" : column.type === "date" ? "date" : "text"}
      step={column.type === "number" ? "0.01" : undefined}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}
