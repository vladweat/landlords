import type { Property } from './property';
import type { Tenant } from './tenant';

export interface Contract {
  id: string;
  account_id: string;
  property_id: string;
  tenant_id: string;
  rent_amount: string;
  currency: string;
  start_date: string;
  end_date: string;
  billing_period: string;
  payment_day: number;
  deposit_amount: string | null;
  auto_generate_charges: boolean;
  status: 'draft' | 'active' | 'ended' | 'overdue' | 'terminated';
  termination_reason: string | null;
  created_at: string;
  property?: Property;
  tenant?: Tenant;
}

export interface LedgerLine {
  date: string;
  type: 'charge' | 'payment';
  description: string;
  amount: string;
  balance: string;
}

export interface Ledger {
  total_expected: string;
  total_paid: string;
  outstanding_balance: string;
  lines: LedgerLine[];
  last_payment_date: string | null;
  overdue_days: number;
}

export type EventType =
  | 'note'
  | 'reminder'
  | 'status_change'
  | 'payment'
  | 'payment_claim'
  | 'termination'
  | 'renewal';

export interface ContractEvent {
  id: string;
  event_type: EventType;
  title: string;
  description: string | null;
  created_at: string;
}

export interface EventsResponse {
  items: ContractEvent[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}
