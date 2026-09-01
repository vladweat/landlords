import { clsx } from 'clsx';
import type { ClassValue } from 'clsx';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatCurrency(amount: number, currency: string = 'RUB'): string {
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency, minimumFractionDigits: 0 }).format(amount);
}

/** Парсит YYYY-MM-DD как локальную дату (без UTC-сдвига дня). */
export function parseLocalDate(date: string | Date): Date {
  if (date instanceof Date) return date;
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(date);
  if (match) {
    return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  }
  return new Date(date);
}

export function formatDate(date: string | Date, pattern: string = 'dd.MM.yyyy'): string {
  return format(parseLocalDate(date), pattern, { locale: ru });
}
