export type AccountType = "bank" | "credit_card";
export type ItemType = "income" | "expense";
export type RecurringTerm = "monthly" | "biweekly";

export type Account = {
  id: number;
  name: string;
  account_type: AccountType;
  opening_balance: number | null;
  opening_balance_date: string | null;
  funding_account_id: number | null;
};

export type RecurringItem = {
  id: number;
  description: string;
  item_type: ItemType;
  amount: number | null;
  day_of_month: number | null;
  start_date: string | null;
  end_date: string | null;
  target_account_id: number;
  category: string | null;
  active: boolean;
  term: RecurringTerm;
};

export type OneOffItem = {
  id: number;
  description: string;
  item_type: ItemType;
  amount: number;
  item_date: string;
  target_account_id: number;
  category: string | null;
};

export type Settings = {
  low_balance_threshold: number;
  model_start_date: string;
  model_end_date: string;
};

export type CreditCard = {
  id: number;
  name: string;
  funding_account_id: number | null;
  funding_account_name: string | null;
};

export type StatementCycle = {
  id: number;
  account_id: number;
  statement_from: string;
  statement_to: string;
  payment_due: string;
  is_generated: boolean;
};

export type StatementTotal = StatementCycle & {
  cycle_id: number;
  account_name: string;
  total: number;
};

export type CashflowMovement = {
  account_id: number;
  account_name: string;
  description: string;
  amount: number;
  kind: "recurring" | "one_off" | "cc_payment";
};

export type CashflowRow = {
  date: string;
  combined: number;
  movements: CashflowMovement[];
  [accountId: string]: string | number | CashflowMovement[];
};

export type CashflowPayload = {
  start: string;
  end: string;
  accounts: { id: number; name: string }[];
  rows: CashflowRow[];
};

export type DashboardPayload = {
  as_of: string;
  threshold: number;
  model_start_date: string;
  model_end_date: string;
  opening_balances_set: boolean;
  accounts: {
    id: number;
    name: string;
    opening_balance: number | null;
    current_balance: number | null;
    first_low_balance_date: string | null;
  }[];
  combined: {
    current_balance: number | null;
    first_low_balance_date: string | null;
  };
  expenses_by_category: { category: string; amount: number }[];
};
