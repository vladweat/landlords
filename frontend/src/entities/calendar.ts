/** Событие календаря платежей. */
export type CalendarEventType = 'charge_due' | 'contract_ending';

export interface CalendarEvent {
  type: CalendarEventType;
  date: string;
  contract_id: string;
  property_address: string;
  tenant_name: string;
  charge_id?: string | null;
  amount?: string | null;
  amount_paid?: string | null;
  remaining?: string | null;
  status?: string | null;
  currency?: string | null;
  rent_amount?: string | null;
  days_until_end?: number | null;
}

export interface CalendarEventsData {
  items: CalendarEvent[];
}
