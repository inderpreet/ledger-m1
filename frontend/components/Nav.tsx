"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

const LINKS: {
  href: string;
  label: string;
  children?: { href: string; label: string }[];
}[] = [
  { href: "/", label: "Dashboard" },
  {
    href: "/expenses",
    label: "Expenses",
    children: [{ href: "/expenses/actual", label: "Actual" }],
  },
  { href: "/bank-flow", label: "Bank Account" },
  {
    href: "/credit-cards",
    label: "Credit Card",
    children: [{ href: "/credit-cards/statements", label: "Statements" }],
  },
  { href: "/setup", label: "Setup" },
];

function linkClass(active: boolean, muted = false) {
  if (active) return "bg-white/12 text-white";
  if (muted) return "text-white/80 hover:bg-white/6 hover:text-white";
  return "text-white/65 hover:bg-white/6 hover:text-white";
}

export function Nav() {
  const pathname = usePathname();
  const router = useRouter();

  async function signOut() {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    router.replace("/login");
  }

  return (
    <aside className="flex w-56 shrink-0 flex-col bg-ink text-[#f3efe4]">
      <div className="border-b border-white/10 px-5 py-6">
        <p className="font-serif text-2xl leading-none tracking-tight">Ledger</p>
        <p className="mt-1 text-[11px] uppercase tracking-[0.18em] text-white/50">
          Cash flow
        </p>
      </div>
      <nav className="flex flex-1 flex-col gap-0.5 p-3">
        {LINKS.map((link) => {
          const active = pathname === link.href;
          const childActive = link.children?.some((child) => pathname === child.href) ?? false;
          return (
            <div key={link.href} className="flex flex-col gap-0.5">
              <Link
                href={link.href}
                className={`rounded-md px-3 py-2 text-sm transition ${linkClass(active, childActive)}`}
              >
                {link.label}
              </Link>
              {link.children?.map((child) => (
                <Link
                  key={child.href}
                  href={child.href}
                  className={`ml-3 rounded-md px-3 py-1.5 text-sm transition ${linkClass(pathname === child.href)}`}
                >
                  {child.label}
                </Link>
              ))}
            </div>
          );
        })}
      </nav>
      <div className="border-t border-white/10 p-3">
        <button
          type="button"
          className="w-full rounded-md px-3 py-2 text-left text-sm text-white/55 hover:bg-white/6 hover:text-white"
          onClick={signOut}
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}
