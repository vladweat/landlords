export type Role = 'owner' | 'manager' | 'accountant';

export type PlanId = 'free' | 'pro' | 'enterprise';

export type SubscriptionStatus = 'none' | 'active' | 'past_due' | 'canceled';

export interface Account {
  id: string;
  name: string;
  owner_id: string;
  base_currency: string;
  timezone: string;
  payment_details?: string | null;
  plan?: PlanId | string;
  subscription_status?: SubscriptionStatus | string;
  subscription_period_end?: string | null;
}

export interface PlanLimits {
  max_properties: number;
  max_users: number;
  max_storage_bytes: number;
}

export interface PlanUsage {
  properties: number;
  users: number;
  storage_bytes: number;
}

export interface PlanCatalogItem {
  id: PlanId | string;
  name: string;
  max_properties: number;
  max_users: number;
  max_storage_bytes: number;
  price_rub_monthly?: number | null;
}

export interface Subscription {
  plan: PlanId | string;
  plan_name: string;
  subscription_status: SubscriptionStatus | string;
  subscription_period_end?: string | null;
  billing_enabled: boolean;
  write_blocked: boolean;
  limits: PlanLimits;
  usage: PlanUsage;
  plans_catalog: PlanCatalogItem[];
}

export interface CheckoutResult {
  confirmation_url: string;
  payment_id: string;
}

export interface Member {
  user_id: string;
  email: string;
  full_name: string;
  phone?: string | null;
  role: Role;
  is_active: boolean;
  membership_id: string;
  created_at: string;
}

export interface Invite {
  id: string;
  account_id: string;
  email: string;
  full_name: string;
  role: Role;
  token: string;
  invite_url: string;
  expires_at: string;
  invited_by_user_id: string;
  created_at: string;
  email_sent?: boolean;
}

export interface InvitePreview {
  email: string;
  full_name: string;
  role: Role;
  account_name: string;
  expires_at: string;
}

export type Permission =
  | 'manage_team'
  | 'manage_account'
  | 'write_properties'
  | 'write_tenants'
  | 'write_contracts'
  | 'write_documents'
  | 'write_payments'
  | 'write_charges'
  | 'write_expenses'
  | 'write_reminders';

const ALL: Permission[] = [
  'manage_team',
  'manage_account',
  'write_properties',
  'write_tenants',
  'write_contracts',
  'write_documents',
  'write_payments',
  'write_charges',
  'write_expenses',
  'write_reminders',
];

const MANAGER: Permission[] = [
  'write_properties',
  'write_tenants',
  'write_contracts',
  'write_documents',
  'write_payments',
  'write_charges',
  'write_expenses',
  'write_reminders',
];

const ACCOUNTANT: Permission[] = [
  'write_payments',
  'write_charges',
  'write_expenses',
  'write_reminders',
];

export const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  owner: ALL,
  manager: MANAGER,
  accountant: ACCOUNTANT,
};

export const ROLE_LABELS: Record<Role, string> = {
  owner: 'Владелец',
  manager: 'Менеджер',
  accountant: 'Бухгалтер',
};

export function hasPermission(role: Role | null | undefined, permission: Permission): boolean {
  if (!role) return false;
  return ROLE_PERMISSIONS[role]?.includes(permission) ?? false;
}
