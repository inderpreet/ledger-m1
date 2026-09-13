"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Nav } from "@/components/Nav";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(pathname === "/login");

  useEffect(() => {
    if (pathname === "/login") {
      setReady(true);
      return;
    }
    let cancelled = false;
    fetch("/api/auth/me", { credentials: "include", cache: "no-store" })
      .then((res) => {
        if (cancelled) return;
        if (res.ok) {
          setReady(true);
          return;
        }
        router.replace("/login");
      })
      .catch(() => {
        if (!cancelled) router.replace("/login");
      });
    return () => {
      cancelled = true;
    };
  }, [pathname, router]);

  if (pathname === "/login") {
    return <div className="min-h-screen flex-1">{children}</div>;
  }

  if (!ready) {
    return (
      <div className="flex min-h-screen flex-1 items-center justify-center text-sm text-ink/50">
        Checking sign-in…
      </div>
    );
  }

  return (
    <>
      <Nav />
      <main className="min-h-screen flex-1 px-8 py-8">{children}</main>
    </>
  );
}
