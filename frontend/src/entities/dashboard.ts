export interface ForecastMonth {
  month: string;
  expected_income: string;
  contracts_ending: number;
}

export interface ForecastAlertItem {
  type: string;
  contract_id: string;
  property_address: string;
  end_date: string;
  monthly_income: string;
  days_until_end: number;
}

export interface ForecastResponse {
  total_to_year_end: string;
  monthly_breakdown: ForecastMonth[];
  alerts: ForecastAlertItem[];
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

export interface LastPayment {
  id: string;
  contract_id: string;
  amount: string;
  date_paid: string;
  method: string;
  property_address: string;
  tenant_name: string;
}
