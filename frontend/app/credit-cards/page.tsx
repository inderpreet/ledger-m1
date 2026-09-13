"use client";

import { CashflowView } from "@/components/CashflowView";

export default function CreditCardsPage() {
  return (
    <CashflowView
      title="Credit Cards"
      subtitle="Card-targeted expenses post here as they happen. On the statement due date the same payment leaves the funding bank and clears that cycle on the card."
      endpoint="/api/cc-cashflow"
    />
  );
}
