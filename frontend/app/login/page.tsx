"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("ledger");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch("/api/auth/status", { credentials: "include", cache: "no-store" })
      .then((res) => res.json())
      .then((body) => setConfigured(Boolean(body.configured)))
      .catch(() => setConfigured(false));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : "Sign-in failed");
      }
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-sm rounded-lg border border-rule bg-card p-6">
        <p className="font-serif text-3xl tracking-tight">Ledger</p>
        <p className="mt-1 text-[11px] uppercase tracking-[0.18em] text-ink/45">Sign in</p>
        {configured === false ? (
          <p className="mt-4 rounded-md border border-clay/30 bg-[#f8ebe6] px-3 py-2 text-sm text-clay">
            No login exists yet. On the server run <code className="tabular">./set-password.sh</code>{" "}
            and save the printed password.
          </p>
        ) : null}
        {error ? (
          <p className="mt-4 rounded-md border border-clay/30 bg-[#f8ebe6] px-3 py-2 text-sm text-clay">
            {error}
          </p>
        ) : null}
        <form className="mt-5 space-y-4" onSubmit={onSubmit}>
          <label className="block text-sm">
            <span className="mb-1 block text-[11px] uppercase tracking-wider text-ink/45">
              Username
            </span>
            <input
              className="w-full rounded-md border border-rule bg-white px-3 py-2"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-[11px] uppercase tracking-wider text-ink/45">
              Password
            </span>
            <input
              type="password"
              className="w-full rounded-md border border-rule bg-white px-3 py-2"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <button
            type="submit"
            className="w-full rounded-md bg-moss px-4 py-2 text-sm font-medium text-white hover:bg-moss-deep disabled:opacity-50"
            disabled={busy || configured === false}
          >
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
}
