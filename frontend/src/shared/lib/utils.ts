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

export function formatDate(date: string | Date, pattern: string = 'dd.MM.yyyy'): string {
  return format(new Date(date), pattern, { locale: ru });
}
