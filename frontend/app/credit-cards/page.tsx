"use client";

import { CashflowView } from "@/components/CashflowView";
import { CreditCardsSubnav } from "@/components/CreditCardsSubnav";
import { PageHeader } from "@/components/PageHeader";

export default function CreditCardsPage() {
  return (
    <div>
      <PageHeader
        title="Credit Card Model"
        subtitle="Card-targeted expenses post here as they happen. On the statement due date the same payment leaves the funding bank and clears that cycle on the card."
      />
      <CreditCardsSubnav />
      <CashflowView hideHeader endpoint="/api/cc-cashflow" />
    </div>
  );
}
