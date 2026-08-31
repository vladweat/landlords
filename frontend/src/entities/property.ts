export interface ActiveContract {
  id: string;
  tenant_name: string;
  status: string;
  end_date: string;
}

export interface ROIData {
  annual_income: string;
  roi: number | null;
  payback_years: number | null;
}

export interface Property {
  id: string;
  account_id: string;
  city: string;
  street: string;
  house: string;
  building?: string;
  apartment?: string;
  address: string;
  type: 'apartment' | 'house' | 'commercial';
  size_m2: number;
  purchase_price: number | null;
  created_at: string;
  active_contract?: ActiveContract | null;
  roi?: ROIData;
}
