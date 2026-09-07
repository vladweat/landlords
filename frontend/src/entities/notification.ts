export type NotificationType = 'charge_overdue' | 'contract_ending';
export type NotificationSeverity = 'warning' | 'critical';

export interface NotificationItem {
  id: string;
  type: NotificationType;
  title: string;
  body: string;
  severity: NotificationSeverity;
  href: string;
  created_at: string;
  meta: Record<string, unknown>;
}

export interface NotificationsData {
  items: NotificationItem[];
  unread_count: number;
}
