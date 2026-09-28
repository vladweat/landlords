export interface Payment {
  id: string;
  account_id: string;
  contract_id: string;
  rent_charge_id: string | null;
  date_paid: string;
  amount: string;
  currency: string;
  method: string;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface PropertyOverviewItem {
  property_id: string;
  address: string;
  tenant_name: string | null;
  contract_status: 'active' | 'overdue' | null;
  monthly_income: string;
  roi: number | null;
  annual_income?: string;
  annual_expenses?: string;
  annual_profit?: string;
  income_is_forecast?: boolean;
  days_until_contract_end: number | null;
}

export interface DashboardSummary {
  monthly_expected_income: string;
  monthly_collected_income: string;
  outstanding_balance: string;
  occupancy_rate: number;
  active_properties: number;
  active_contracts: number;
  monthly_income_previous: string;
  monthly_income_change_percent: number;
  overdue_total_amount: string;
  overdue_count: number;
  portfolio_roi?: {
    portfolio_roi: number;
    properties_with_roi: number;
  };
  properties_overview?: PropertyOverviewItem[];
}
