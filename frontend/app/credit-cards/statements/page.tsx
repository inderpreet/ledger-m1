"use client";

import { CreditCardSetup } from "@/components/CreditCardSetup";
import { CreditCardsSubnav } from "@/components/CreditCardsSubnav";
import { PageHeader } from "@/components/PageHeader";

export default function CreditCardStatementsPage() {
  return (
    <div>
      <PageHeader
        title="Statements"
        subtitle="Charges stay on the card until the funding account is debited on payment due. Set funding and statement cycles here."
      />
      <CreditCardsSubnav />
      <CreditCardSetup />
    </div>
  );
}
