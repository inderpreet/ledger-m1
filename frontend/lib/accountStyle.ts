export type AccountTone = "scotia" | "td" | "neutral";

export function accountTone(name: string): AccountTone {
  const n = name.toLowerCase();
  if (n.includes("scotia")) return "scotia";
  if (n.includes("td")) return "td";
  return "neutral";
}

export function accountTextClass(name: string): string {
  switch (accountTone(name)) {
    case "scotia":
      return "text-scotia";
    case "td":
      return "text-td";
    default:
      return "text-ink";
  }
}

export function accountHex(name: string): string {
  switch (accountTone(name)) {
    case "scotia":
      return "#c42b2b";
    case "td":
      return "#187a3c";
    default:
      return "#1c2218";
  }
}
