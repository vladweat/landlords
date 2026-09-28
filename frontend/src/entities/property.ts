export type PropertyType = 'apartment' | 'house' | 'room' | 'commercial';

export const PROPERTY_TYPE_LABELS: Record<PropertyType, string> = {
  apartment: 'Квартира',
  house: 'Дом',
  room: 'Комната',
  commercial: 'Коммерция',
};

export interface ActiveContract {
  id: string;
  tenant_name: string;
  status: string;
  end_date: string;
}

export interface ROIData {
  annual_income: string;
  annual_expenses: string;
  annual_profit: string;
  roi: number | null;
  payback_years: number | null;
  income_is_forecast?: boolean;
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
  type: PropertyType;
  size_m2: number;
  purchase_price: string | null;
  created_at: string;
  active_contract?: ActiveContract | null;
  roi?: ROIData;
}
