"use client";

import { OneOffTable } from "@/components/OneOffTable";
import { PageHeader } from "@/components/PageHeader";
import { RecurringTable } from "@/components/RecurringTable";

export default function ExpensesPage() {
  return (
    <div>
      <PageHeader
        title="Expenses"
        subtitle="Recurring items fire monthly or every two weeks. One-off items post on an exact date."
      />
      <section className="mb-10">
        <h2 className="mb-3 font-serif text-xl tracking-tight">Recurring</h2>
        <p className="mb-4 text-sm text-ink/55">
          Monthly items use the day of month. Bi-weekly items use Start, then every two weeks after
          that.
        </p>
        <RecurringTable />
      </section>
      <section>
        <h2 className="mb-3 font-serif text-xl tracking-tight">One-off</h2>
        <p className="mb-4 text-sm text-ink/55">
          Exact-date income and expenses. Card-targeted rows wait until the statement due date to
          hit a bank account.
        </p>
        <OneOffTable />
      </section>
    </div>
  );
}
