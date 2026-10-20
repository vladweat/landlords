export interface PortalHistoryLine {
  date: string;
  type: 'charge' | 'payment' | string;
  description: string;
  amount: string;
  balance: string;
}

export interface PortalOpenCharge {
  charge_id: string;
  period_start: string;
  period_end: string;
  due_date: string;
  amount: string;
  amount_paid: string;
  amount_remaining: string;
  currency: string;
  status: string;
  invoice_url: string | null;
}

export interface PaymentClaim {
  id: string;
  contract_id: string;
  charge_id: string | null;
  amount: string | null;
  note: string | null;
  status: 'pending' | 'dismissed' | 'confirmed' | string;
  created_at: string;
  resolved_at: string | null;
}

export interface PublicPortal {
  landlord_name: string;
  property_address: string;
  tenant_name: string;
  currency: string;
  outstanding_balance: string;
  total_expected: string;
  total_paid: string;
  payment_details: string | null;
  history: PortalHistoryLine[];
  open_charges: PortalOpenCharge[];
  pending_claim: PaymentClaim | null;
}

export interface PortalLink {
  portal_token: string;
  share_url: string;
  portal_token_expires_at: string;
}
