import { AccountName } from "@/components/AccountName";
import { daysUntil, formatMoney } from "@/lib/format";
import type { DashboardPayload } from "@/lib/types";

export function LowBalanceBanner({ data }: { data: DashboardPayload }) {
  const alerts = [
    ...data.accounts.map((a) => ({
      name: a.name,
      date: a.first_low_balance_date,
      balance: a.current_balance,
    })),
    {
      name: "Combined",
      date: data.combined.first_low_balance_date,
      balance: data.combined.current_balance,
    },
  ].filter((a) => {
    const days = daysUntil(a.date);
    return days !== null && days <= 30;
  });

  if (alerts.length === 0) return null;

  return (
    <div className="mb-6 rounded-lg border border-clay/30 bg-[#f8ebe6] px-4 py-3 text-sm text-clay">
      <p className="font-medium">Low-balance warning (within 30 days)</p>
      <ul className="mt-1 space-y-0.5">
        {alerts.map((a) => (
          <li key={a.name}>
            <AccountName name={a.name} /> drops below {formatMoney(data.threshold)} on {a.date} (
            {daysUntil(a.date)} days)
          </li>
        ))}
      </ul>
    </div>
  );
}
