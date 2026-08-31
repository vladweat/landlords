export interface TenantActiveContract {
  id: string;
  property_address: string;
  status: string;
  rent_amount: string;
  end_date: string;
}

export interface Tenant {
  id: string;
  account_id: string;
  full_name: string;
  email: string;
  phone: string;
  created_at: string;
  active_contracts?: TenantActiveContract[];
}
