export const money = new Intl.NumberFormat("en-CA", {
  style: "currency",
  currency: "CAD",
});

export function formatMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return money.format(value);
}

export function daysUntil(iso: string | null, from = new Date()): number | null {
  if (!iso) return null;
  const target = new Date(`${iso}T00:00:00`);
  const start = new Date(from);
  start.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - start.getTime()) / 86_400_000);
}

export function isoToday(): string {
  return new Date().toISOString().slice(0, 10);
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function weekdayShort(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return "";
  return WEEKDAYS[d.getDay()] ?? "";
}

export function formatDateWithDay(iso: string | null | undefined): string {
  if (!iso) return "—";
  const day = weekdayShort(iso);
  return day ? `${iso} ${day}` : iso;
}

export function addDaysIso(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + days);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

/** First payday is start; the following payday is two weeks later. */
export function nextBiweeklyDate(startIso: string | null | undefined): string | null {
  if (!startIso) return null;
  return addDaysIso(startIso, 14);
}

export function formatBiweeklyWhen(startIso: string | null | undefined): string {
  if (!startIso) return "Set start date";
  const next = nextBiweeklyDate(startIso);
  return `${formatDateWithDay(startIso)} → ${formatDateWithDay(next)}`;
}
