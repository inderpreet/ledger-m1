"use client";

import { useState } from "react";
import { BudgetTable } from "@/components/BudgetTable";
import { ExpensesSubnav } from "@/components/ExpensesSubnav";
import { PageHeader } from "@/components/PageHeader";
import { RecurringTable } from "@/components/RecurringTable";

export default function ExpensesPage() {
  const [budgetEpoch, setBudgetEpoch] = useState(0);

  return (
    <div>
      <PageHeader
        title="Expenses"
        subtitle="Budget categories and recurring items grouped against those budgets."
      />
      <ExpensesSubnav />
      <section className="mb-10 rounded-lg border border-rule border-l-4 border-l-moss bg-card p-5">
        <p className="mb-1 text-[11px] uppercase tracking-[0.16em] text-moss">Catalog</p>
        <h2 className="mb-2 font-serif text-xl tracking-tight">Budgets</h2>
        <p className="mb-4 text-sm text-ink/55">
          Add categories such as Utilities, Insurance, or Mortgage, then set a monthly, bi-weekly,
          or yearly amount. Recurring expenses below are grouped against these. Renaming updates
          matching rows; deleting clears the category on those rows.
        </p>
        <BudgetTable onChanged={() => setBudgetEpoch((n) => n + 1)} />
      </section>
      <section className="border-t border-rule pt-10">
        <h2 className="mb-3 font-serif text-xl tracking-tight">Recurring</h2>
        <p className="mb-4 text-sm text-ink/55">
          Grouped by budget category. Monthly totals count active income and expenses. Bi-weekly
          amounts (items and budgets) use 26 pays / 12 months; yearly budgets are divided by 12.
        </p>
        <RecurringTable key={budgetEpoch} />
      </section>
    </div>
  );
}
