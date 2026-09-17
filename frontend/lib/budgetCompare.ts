import type { BudgetCategory } from "@/lib/categories";
import type { RecurringItem } from "@/lib/types";

const UNC = "Uncategorized";

export function monthlyRecurringAmount(item: RecurringItem): number | null {
  if (!item.active || item.amount == null) return null;
  if (item.term === "biweekly") return (item.amount * 26) / 12;
  return item.amount;
}

export function monthlyRecurringExpense(item: RecurringItem): number | null {
  if (item.item_type !== "expense") return null;
  return monthlyRecurringAmount(item);
}

export function monthlyRecurringIncome(item: RecurringItem): number | null {
  if (item.item_type !== "income") return null;
  return monthlyRecurringAmount(item);
}

export function monthlyBudgetAmount(category: BudgetCategory | null | undefined): number | null {
  if (!category || category.amount == null) return null;
  if (category.period === "yearly") return category.amount / 12;
  if (category.period === "biweekly") return (category.amount * 26) / 12;
  return category.amount;
}

export function monthlyToPeriod(monthly: number, period: BudgetCategory["period"]): number {
  if (period === "yearly") return monthly * 12;
  if (period === "biweekly") return (monthly * 12) / 26;
  return monthly;
}

export function calculatedBudgetFromItems(
  items: RecurringItem[],
  category: BudgetCategory,
): number {
  const spent = sumMonthly(items, monthlyRecurringExpense);
  const income = sumMonthly(items, monthlyRecurringIncome);
  const monthly = spent > 0.005 ? spent : income;
  return monthlyToPeriod(monthly, category.period);
}

function sumMonthly(
  items: RecurringItem[],
  pick: (item: RecurringItem) => number | null,
): number {
  return items.reduce((sum, item) => {
    const monthly = pick(item);
    return monthly == null ? sum : sum + monthly;
  }, 0);
}

export function categoryMonthlyTotal(items: RecurringItem[]): number {
  return sumMonthly(items, monthlyRecurringExpense);
}

export type RecurringCategoryGroup = {
  key: string;
  name: string;
  items: RecurringItem[];
  budget: BudgetCategory | null;
  spent: number;
  income: number;
  budgeted: number | null;
};

export function groupRecurringByCategory(
  items: RecurringItem[],
  budgets: BudgetCategory[],
): RecurringCategoryGroup[] {
  const byName = new Map(budgets.map((c) => [c.name, c]));
  const buckets = new Map<string, RecurringItem[]>();
  for (const item of items) {
    const key = item.category?.trim() || UNC;
    const list = buckets.get(key) ?? [];
    list.push(item);
    buckets.set(key, list);
  }

  const keys = new Set<string>([...budgets.map((c) => c.name), ...buckets.keys()]);
  const ordered = [...keys].sort((a, b) => {
    if (a === UNC) return 1;
    if (b === UNC) return -1;
    return a.localeCompare(b);
  });

  return ordered
    .map((name) => {
      const groupItems = buckets.get(name) ?? [];
      const budget = byName.get(name) ?? null;
      return {
        key: name,
        name,
        items: groupItems,
        budget,
        spent: sumMonthly(groupItems, monthlyRecurringExpense),
        income: sumMonthly(groupItems, monthlyRecurringIncome),
        budgeted: monthlyBudgetAmount(budget),
      };
    })
    .filter((group) => group.items.length > 0 || group.budgeted != null);
}
