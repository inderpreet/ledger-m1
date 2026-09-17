"use client";

import { useState } from "react";
import { BudgetTable } from "@/components/BudgetTable";
import { ExpensesSubnav } from "@/components/ExpensesSubnav";
import { PageHeader } from "@/components/PageHeader";
import { RecurringTable } from "@/components/RecurringTable";

export default function ExpensesPage() {
  const [budgetEpoch, setBudgetEpoch] = useState(0);
  const [itemEpoch, setItemEpoch] = useState(0);

  return (
    <div>
      <PageHeader
        title="Expenses"
        subtitle="Create budget categories, assign recurring items to them, then compare calculated totals to the amount you entered."
      />
      <ExpensesSubnav />
      <section className="mb-10 rounded-lg border border-rule border-l-4 border-l-moss bg-card p-5">
        <p className="mb-1 text-[11px] uppercase tracking-[0.16em] text-moss">Catalog</p>
        <h2 className="mb-2 font-serif text-xl tracking-tight">Budgets</h2>
        <p className="mb-4 text-sm text-ink/55">
          Add a category to populate the Recurring dropdown. Enter the amount you want, then assign
          monthly or bi-weekly items below. Calculated sums those items in the same period as Amount.
        </p>
        <BudgetTable
          refreshKey={itemEpoch}
          onChanged={() => setBudgetEpoch((n) => n + 1)}
        />
      </section>
      <section className="border-t border-rule pt-10">
        <h2 className="mb-3 font-serif text-xl tracking-tight">Recurring</h2>
        <p className="mb-4 text-sm text-ink/55">
          Grouped by budget category. Pick a category on each row. Bi-weekly amounts use 26 pays /
          12 months when rolled into a monthly or yearly budget.
        </p>
        <RecurringTable key={budgetEpoch} onChanged={() => setItemEpoch((n) => n + 1)} />
      </section>
    </div>
  );
}
