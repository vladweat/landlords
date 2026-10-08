import { parseLocalDate } from '@/shared/lib/utils';
import type { ChargeRow } from '@/features/contracts/components/ChargePeriodsList';

export const contractStatusLabels: Record<string, string> = {
  draft: 'Черновик',
  active: 'Активен',
  ended: 'Завершён',
  overdue: 'Просрочен',
  terminated: 'Расторгнут',
};

export const contractStatusDots: Record<string, string> = {
  draft: 'bg-gray-400',
  active: 'bg-emerald-500',
  ended: 'bg-blue-500',
  overdue: 'bg-red-500',
  terminated: 'bg-amber-500',
};

export function formatContractMoney(value: number | string, currency: string): string {
  const n = typeof value === 'string' ? Number(value) : value;
  const suffix = currency === 'RUB' ? '₽' : currency;
  return `${n.toLocaleString('ru-RU')} ${suffix}`;
}

export function chargeRemaining(c: ChargeRow): number {
  return Math.max(0, Number(c.amount) - Number(c.amount_paid || 0));
}

function daysUntil(dateStr: string): number {
  const target = parseLocalDate(dateStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

export function daysLeftLabel(endDate: string): string | null {
  const days = daysUntil(endDate);
  if (days < 0) return `завершён ${Math.abs(days)} дн. назад`;
  if (days === 0) return 'заканчивается сегодня';
  if (days === 1) return 'остался 1 день';
  if (days < 5) return `осталось ${days} дня`;
  return `осталось ${days} дн.`;
}
