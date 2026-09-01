export type ExpenseCategory =
  | 'utilities'
  | 'repair'
  | 'tax'
  | 'realtor_fee'
  | 'other';

export interface PropertyExpense {
  id: string;
  account_id: string;
  property_id: string;
  category: ExpenseCategory;
  amount: string;
  currency: string;
  date_incurred: string;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export const EXPENSE_CATEGORY_LABELS: Record<ExpenseCategory, string> = {
  utilities: 'ЖКХ',
  repair: 'Ремонт',
  tax: 'Налоги',
  realtor_fee: 'Комиссия риелтора',
  other: 'Прочее',
};
