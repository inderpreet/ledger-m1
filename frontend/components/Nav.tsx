"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/bank-flow", label: "Bank Account Flow" },
  { href: "/credit-cards", label: "Credit Cards" },
  { href: "/expenses", label: "Expenses" },
  { href: "/setup", label: "Setup" },
];

export function Nav() {
  const pathname = usePathname();
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
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`rounded-md px-3 py-2 text-sm transition ${
                active
                  ? "bg-white/12 text-white"
                  : "text-white/65 hover:bg-white/6 hover:text-white"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
