export interface Invoice {
  invoice_id: string;
  charge_id: string;
  contract_id: string;
  document_id: string | null;
  share_url: string;
  public_token: string;
  public_token_expires_at: string;
}

export interface PublicInvoice {
  landlord_name: string;
  property_address: string;
  tenant_name: string;
  period_start: string;
  period_end: string;
  due_date: string;
  amount: string;
  amount_paid: string;
  amount_remaining: string;
  currency: string;
  status: string;
  payment_details: string | null;
  filename: string | null;
  has_pending_claim: boolean;
}
