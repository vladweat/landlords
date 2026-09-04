export type Role = 'owner' | 'manager' | 'accountant';

export interface Account {
  id: string;
  name: string;
  owner_id: string;
  base_currency: string;
  timezone: string;
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
