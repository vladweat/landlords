import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import type { CalendarEvent } from '@/entities/calendar';
import { formatDate, parseLocalDate } from '@/shared/lib/utils';
import { shortAddress } from '@/shared/lib/address';

const typeLabels: Record<string, string> = {
  charge_due: 'К оплате',
  contract_ending: 'Окончание договора',
};

const statusDots: Record<string, string> = {
  pending: 'bg-blue-500',
  partially_paid: 'bg-amber-500',
  overdue: 'bg-red-500',
  paid: 'bg-emerald-500',
};

function daysLabel(event: CalendarEvent, today: Date): string {
  const eventDate = parseLocalDate(event.date);
  const diff = Math.round((eventDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  if (event.type === 'charge_due' && event.status === 'overdue') {
    return diff === 0 ? 'сегодня' : `${Math.abs(diff)} дн. просрочки`;
  }
  if (event.type === 'contract_ending' && event.days_until_end != null) {
    if (event.days_until_end === 0) return 'сегодня';
    if (event.days_until_end < 0) return `${Math.abs(event.days_until_end)} дн. назад`;
    return `через ${event.days_until_end} дн.`;
  }
  if (diff === 0) return 'сегодня';
  if (diff === 1) return 'завтра';
  if (diff < 0) return `${Math.abs(diff)} дн. назад`;
  return `через ${diff} дн.`;
}

function amountLabel(event: CalendarEvent): string | null {
  if (event.type === 'charge_due' && event.remaining != null) {
    return `${Number(event.remaining).toLocaleString('ru-RU')} ₽`;
  }
  if (event.type === 'contract_ending' && event.rent_amount != null) {
    return `${Number(event.rent_amount).toLocaleString('ru-RU')} ₽/мес`;
  }
  return null;
}

interface CalendarEventRowProps {
  event: CalendarEvent;
  today: Date;
}

export function CalendarEventRow({ event, today }: CalendarEventRowProps) {
  const isOverdue = event.type === 'charge_due' && event.status === 'overdue';
  const badge =
    isOverdue ? 'Просрочка' : typeLabels[event.type] || event.type;
  const amount = amountLabel(event);
  const dotClass =
    event.type === 'charge_due'
      ? statusDots[event.status || 'pending'] || 'bg-gray-400'
      : 'bg-violet-500';

  return (
    <Link
      to={`/contracts/${event.contract_id}`}
      className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-50 last:border-0"
    >
      <div className="w-16 flex-shrink-0 text-sm text-gray-500">
        {formatDate(event.date, 'd MMM')}
      </div>
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <span className={`h-2 w-2 shrink-0 rounded-full ${dotClass}`} />
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                isOverdue ? 'bg-red-50 text-red-700' : 'bg-gray-100 text-gray-600'
              }`}
            >
              {badge}
            </span>
            <span className="text-sm text-gray-500">{daysLabel(event, today)}</span>
          </div>
          <p className="text-sm text-gray-900 truncate mt-0.5">
            {shortAddress(event.property_address || '—')}
            {event.tenant_name ? ` · ${event.tenant_name}` : ''}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {amount && (
          <span className={`text-sm font-medium ${isOverdue ? 'text-red-600' : 'text-gray-900'}`}>
            {amount}
          </span>
        )}
        <ArrowRight className="h-4 w-4 text-gray-300" />
      </div>
    </Link>
  );
}
