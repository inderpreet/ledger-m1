export type BudgetCategory = {
  id: number;
  name: string;
  amount: number | null;
  period: "monthly" | "biweekly" | "yearly";
};

export function categorySelectOptions(
  categories: BudgetCategory[],
  current?: string | null | Array<string | null | undefined>,
): { value: string; label: string }[] {
  const names = new Set(categories.map((c) => c.name));
  const values = Array.isArray(current) ? current : [current];
  const extras = [
    ...new Set(values.filter((c): c is string => Boolean(c) && !names.has(c as string))),
  ].map((c) => ({ value: c, label: `${c} (not in Budgets)` }));
  return [
    { value: "", label: "—" },
    ...extras,
    ...categories.map((c) => ({ value: c.name, label: c.name })),
  ];
}
