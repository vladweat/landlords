export interface ForecastMonth {
  month: string;
  expected_income: number;
  contracts_ending: number;
}

export interface ForecastAlertItem {
  type: string;
  contract_id: string;
  property_address: string;
  end_date: string;
  monthly_income: number;
  days_until_end: number;
}

export interface ForecastResponse {
  total_to_year_end: number;
  monthly_breakdown: ForecastMonth[];
  alerts: ForecastAlertItem[];
}

export interface PropertyOverview {
  id: string;
  address: string;
  tenant_name: string | null;
  contract_status: 'active' | 'overdue' | null;
  monthly_income: string;
  roi: number | null;
  days_until_contract_end: number | null;
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
