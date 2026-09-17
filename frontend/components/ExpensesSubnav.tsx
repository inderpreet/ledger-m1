"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/expenses", label: "Recurring" },
  { href: "/expenses/actual", label: "Actual" },
];

export function ExpensesSubnav() {
  const pathname = usePathname();
  return (
    <div className="mb-6 flex gap-1 border-b border-rule">
      {TABS.map((tab) => {
        const active = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${
              active ? "border-moss text-ink" : "border-transparent text-ink/50 hover:text-ink"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </div>
  );
}
