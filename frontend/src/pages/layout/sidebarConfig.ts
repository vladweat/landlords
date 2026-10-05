import {
  LayoutDashboard,
  Building2,
  Users,
  FileText,
  CreditCard,
  CalendarDays,
  Wallet,
  BarChart3,
  Settings,
  User,
  type LucideIcon,
} from 'lucide-react';
import type { Role } from '@/entities/account';

export type NavBadgeKey = 'overdue_payments' | 'ending_contracts' | 'billing_issue';

export interface NavChild {
  id: string;
  label: string;
  href: string;
  /** Если задано — пункт виден только при наличии права. */
  requiredPermission?: 'manage_team' | 'manage_account';
}

export interface NavItem {
  id: string;
  label: string;
  href: string;
  icon: LucideIcon;
  /** Роли, которым пункт виден. Если не задано — всем. */
  visibleForRoles?: Role[];
  badgeKey?: NavBadgeKey;
  children?: NavChild[];
}

export interface NavSection {
  id: string;
  label: string;
  items: NavItem[];
}

/** Секции настроек — и для сайдбара, и для страницы настроек. */
export const SETTINGS_SECTIONS: NavChild[] = [
  { id: 'personal', label: 'Личное', href: '/settings#personal' },
  { id: 'account', label: 'Аккаунт', href: '/settings#account' },
  {
    id: 'team',
    label: 'Команда и роли',
    href: '/settings#team',
    requiredPermission: 'manage_team',
  },
  { id: 'documents', label: 'Договоры и данные', href: '/settings#documents' },
];

export const NAV_SECTIONS: NavSection[] = [
  {
    id: 'work',
    label: 'Работа',
    items: [
      {
        id: 'dashboard',
        label: 'Дашборд',
        href: '/dashboard',
        icon: LayoutDashboard,
      },
      {
        id: 'properties',
        label: 'Объекты',
        href: '/properties',
        icon: Building2,
        visibleForRoles: ['owner', 'manager'],
      },
      {
        id: 'tenants',
        label: 'Арендаторы',
        href: '/tenants',
        icon: Users,
        visibleForRoles: ['owner', 'manager'],
      },
      {
        id: 'contracts',
        label: 'Договоры',
        href: '/contracts',
        icon: FileText,
        visibleForRoles: ['owner', 'manager'],
        badgeKey: 'ending_contracts',
      },
      {
        id: 'calendar',
        label: 'Календарь',
        href: '/calendar',
        icon: CalendarDays,
      },
    ],
  },
  {
    id: 'finance',
    label: 'Финансы',
    items: [
      {
        id: 'payments',
        label: 'Платежи',
        href: '/payments',
        icon: CreditCard,
        badgeKey: 'overdue_payments',
      },
      {
        id: 'expenses',
        label: 'Расходы',
        href: '/expenses',
        icon: Wallet,
      },
      {
        id: 'reports',
        label: 'Отчёты',
        href: '/reports',
        icon: BarChart3,
      },
    ],
  },
  {
    id: 'account',
    label: 'Аккаунт',
    items: [
      {
        id: 'settings',
        label: 'Настройки',
        href: '/settings',
        icon: Settings,
        badgeKey: 'billing_issue',
        children: SETTINGS_SECTIONS,
      },
    ],
  },
];

export const SIDEBAR_COLLAPSED_KEY = 'sidebar_collapsed';

export function isNavItemVisible(item: NavItem, role: Role | null): boolean {
  if (!item.visibleForRoles) return true;
  if (!role) return false;
  return item.visibleForRoles.includes(role);
}

export function findActiveNavLabel(pathname: string): string | null {
  for (const section of NAV_SECTIONS) {
    for (const item of section.items) {
      if (pathname.startsWith(item.href)) return item.label;
    }
  }
  return null;
}

/** Иконка профиля в футере сайдбара. */
export const ProfileIcon = User;
