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

function actionHint(event: CalendarEvent): string {
  if (event.type === 'charge_due' && event.status === 'overdue') return 'Записать платёж';
  if (event.type === 'charge_due') return 'К договору';
  return 'Продлить / открыть';
}

interface CalendarEventRowProps {
  event: CalendarEvent;
  today: Date;
  /** Подсказка действия (на дашборде обычно скрыта). */
  showActionHint?: boolean;
}

export function CalendarEventRow({ event, today, showActionHint = true }: CalendarEventRowProps) {
  const isOverdue = event.type === 'charge_due' && event.status === 'overdue';
  const badge = isOverdue ? 'Просрочка' : typeLabels[event.type] || event.type;
  const amount = amountLabel(event);
  const dotClass =
    event.type === 'charge_due'
      ? statusDots[event.status || 'pending'] || 'bg-gray-400'
      : 'bg-violet-500';

  return (
    <Link
      to={`/contracts/${event.contract_id}`}
      className="flex items-start gap-2.5 px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-50 last:border-0"
    >
      <div className="w-10 flex-shrink-0 pt-0.5 text-center">
        <p className="text-sm font-semibold text-gray-800 leading-none">
          {formatDate(event.date, 'd')}
        </p>
        <p className="text-[11px] text-gray-400 mt-0.5 leading-none uppercase">
          {formatDate(event.date, 'MMM')}
        </p>
      </div>

      <div className="flex items-start gap-2 min-w-0 flex-1">
        <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${dotClass}`} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 min-w-0">
            <span
              className={`text-[11px] font-medium px-1.5 py-0.5 rounded shrink-0 ${
                isOverdue ? 'bg-red-50 text-red-700' : 'bg-gray-100 text-gray-600'
              }`}
            >
              {badge}
            </span>
            <span className="text-xs text-gray-400 truncate">{daysLabel(event, today)}</span>
          </div>
          <div className="mt-0.5 flex items-center justify-between gap-2 min-w-0">
            <p className="text-sm text-gray-900 truncate">
              {shortAddress(event.property_address || '—')}
              {event.tenant_name ? ` · ${event.tenant_name}` : ''}
            </p>
            {amount && (
              <span
                className={`text-xs font-medium tabular-nums shrink-0 ${
                  isOverdue ? 'text-red-600' : 'text-gray-700'
                }`}
              >
                {amount}
              </span>
            )}
          </div>
          {showActionHint && (
            <p className={`text-xs mt-0.5 truncate ${isOverdue ? 'text-red-600' : 'text-blue-600'}`}>
              {actionHint(event)}
            </p>
          )}
        </div>
      </div>

      <ArrowRight className="h-4 w-4 text-gray-300 flex-shrink-0 mt-1" />
    </Link>
  );
}
