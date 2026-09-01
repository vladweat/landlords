export interface Payment {
  property_id: string;
  contract_property_id: string;
  amount: string;
  date_paproperty_id: string;
  currency: string;
  method: string;
  note: string | null;
  rent_charge_id: string | null;
  created_at: string;
}

export interface PropertyOverviewItem {
  property_id: string;
  address: string;
  tenant_name: string | null;
  contract_status: 'active' | 'overdue' | null;
  monthly_income: number;
  roi: number | null;
  annual_income?: string;
  annual_expenses?: string;
  annual_profit?: string;
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
  portfolio_roi?: {
    portfolio_roi: number;
    properties_with_roi: number;
  };
  properties_overview?: PropertyOverviewItem[];
}
