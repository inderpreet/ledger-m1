"use client";

import { ExpensesSubnav } from "@/components/ExpensesSubnav";
import { OneOffTable } from "@/components/OneOffTable";
import { PageHeader } from "@/components/PageHeader";

export default function ExpensesActualPage() {
  return (
    <div>
      <PageHeader
        title="Expenses Actual"
        subtitle="Exact-date income and expenses. Card-targeted rows wait until the statement due date to hit a bank account."
      />
      <ExpensesSubnav />
      <OneOffTable />
    </div>
  );
}
