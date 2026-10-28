import { Link } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import type { ForecastAlertItem } from '@/entities/dashboard';
import { parseLocalDate } from '@/shared/lib/utils';

function daysUntil(dateStr: string): number {
  const target = parseLocalDate(dateStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = target.getTime() - today.getTime();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

function formatDays(n: number): string {
  if (n <= 0) return 'сегодня';
  if (n === 1) return 'завтра';
  if (n < 5) return `${n} дня`;
  return `${n} дней`;
}

interface ForecastAlertProps {
  alert: ForecastAlertItem;
}

export function ForecastAlert({ alert }: ForecastAlertProps) {
  const left = daysUntil(alert.end_date);
  const isUrgent = left <= 7;

  return (
    <div className={`flex items-center justify-between rounded-lg px-3 py-2 text-xs ${isUrgent ? 'bg-red-50 border border-red-200' : 'bg-amber-50 border border-amber-200'}`}>
      <div className="flex items-center gap-2 min-w-0">
        <AlertTriangle className={`h-3.5 w-3.5 flex-shrink-0 ${isUrgent ? 'text-red-600' : 'text-amber-600'}`} />
        <span className={isUrgent ? 'text-red-800' : 'text-amber-800'}>
          <span className="font-medium">{alert.property_address.split(',').slice(1, 3).join(',').trim()}</span>
          {' — '}
          {left > 0 ? `закончится через ${formatDays(left)}` : 'закончился'}
          {', '}
          <span className="font-medium">-{Number(alert.monthly_income).toLocaleString('ru-RU')} ₽/мес</span>
        </span>
      </div>
      <Link to={`/contracts/${alert.contract_id}`} className="flex-shrink-0 ml-2 text-xs font-medium text-blue-600 hover:text-blue-800">
        К контракту
      </Link>
    </div>
  );
}
