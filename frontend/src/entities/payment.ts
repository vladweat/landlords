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
