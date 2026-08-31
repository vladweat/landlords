export interface ReminderResponse {
  id: string;
  charge_id: string;
  reminder_type: string;
  message_text: string;
  created_at: string;
}

export interface ReminderRequest {
  charge_id: string;
  reminder_type: 'first' | 'second' | 'third';
}
