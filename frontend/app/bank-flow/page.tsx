"use client";

import { CashflowView } from "@/components/CashflowView";

export default function BankFlowPage() {
  return (
    <CashflowView
      title="Bank Account Flow"
      subtitle="End-of-day bank balances. Activity lists what posted that day."
      endpoint="/api/daily-cashflow"
    />
  );
}
