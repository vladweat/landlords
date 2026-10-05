import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { addDays, format } from 'date-fns';
import { AlertTriangle, ArrowRight, CalendarClock, Inbox } from 'lucide-react';
import { calendarApi } from '@/features/calendar/api';
import { CalendarEventRow } from '@/features/calendar/components/CalendarEventRow';
import { Skeleton } from '@/shared/ui/Skeleton';
import { DashboardSection } from './DashboardSection';

interface AttentionFeedProps {
  overdueChargesCount: number;
  overdueChargesAmount: string;
  overdueContractsCount: number;
}

function overdueChargesLabel(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return `${count} просроченное начисление`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return `${count} просроченных начисления`;
  }
  return `${count} просроченных начислений`;
}

function overdueContractsLabel(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return `${count} договор с просрочкой`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return `${count} договора с просрочкой`;
  }
  return `${count} договоров с просрочкой`;
}

const EVENTS_LIMIT = 5;

/** Единая лента внимания: просрочки и ближайшие события в одном списке. */
export function AttentionFeed({
  overdueChargesCount,
  overdueChargesAmount,
  overdueContractsCount,
}: AttentionFeedProps) {
  const queryClient = useQueryClient();
  const today = useMemo(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), d.getDate());
  }, []);

  const from = format(today, 'yyyy-MM-dd');
  const to = format(addDays(today, 45), 'yyyy-MM-dd');

  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: ['calendar-events', from, to],
    queryFn: () => calendarApi.getEvents({ from, to }),
  });

  const preview = (data?.items ?? []).slice(0, EVENTS_LIMIT);
  const totalEvents = data?.items.length ?? 0;
  const hasAlerts = overdueChargesCount > 0 || overdueContractsCount > 0;
  const isEmpty = !hasAlerts && preview.length === 0 && !isLoading && !isError;

  return (
    <DashboardSection
      title="Требует внимания"
      icon={<Inbox className="h-4 w-4 text-blue-600" />}
      action={{
        label: totalEvents > EVENTS_LIMIT ? `Календарь (${totalEvents})` : 'Календарь',
        to: '/calendar',
      }}
      flush
      bodyClassName="p-0"
    >
      {hasAlerts && (
        <div className="divide-y divide-gray-100 border-b border-gray-100">
          {overdueChargesCount > 0 && (
            <Link
              to="/calendar"
              className="flex items-center gap-3 px-4 py-3 hover:bg-red-50/60 transition-colors"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 flex-shrink-0">
                <AlertTriangle className="h-4 w-4 text-red-600" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900">
                  {overdueChargesLabel(overdueChargesCount)}
                </p>
                <p className="text-xs text-red-600 tabular-nums">
                  {Number(overdueChargesAmount).toLocaleString('ru-RU')} ₽
                </p>
              </div>
              <ArrowRight className="h-4 w-4 text-gray-300 flex-shrink-0" />
            </Link>
          )}
          {overdueContractsCount > 0 && (
            <Link
              to="/contracts?status=overdue"
              className="flex items-center gap-3 px-4 py-3 hover:bg-amber-50/60 transition-colors"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-50 flex-shrink-0">
                <CalendarClock className="h-4 w-4 text-amber-600" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900">
                  {overdueContractsLabel(overdueContractsCount)}
                </p>
                <p className="text-xs text-amber-700">Проверьте статус или продление</p>
              </div>
              <ArrowRight className="h-4 w-4 text-gray-300 flex-shrink-0" />
            </Link>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="p-4 space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : isError ? (
        <div className="px-4 py-5 text-center">
          <p className="text-sm text-red-500 mb-2">Не удалось загрузить события</p>
          <button
            type="button"
            onClick={() =>
              queryClient.invalidateQueries({ queryKey: ['calendar-events', from, to] })
            }
            className="text-sm font-medium text-blue-600 hover:text-blue-800"
            disabled={isFetching}
          >
            Повторить
          </button>
        </div>
      ) : isEmpty ? (
        <div className="px-4 py-6 text-center">
          <p className="text-sm text-emerald-700">Всё спокойно — срочных задач нет</p>
        </div>
      ) : preview.length > 0 ? (
        <div>
          {hasAlerts && (
            <p className="px-4 pt-3 pb-1 text-[11px] font-medium uppercase tracking-wide text-gray-400">
              Ближайшие события
            </p>
          )}
          {preview.map((event) => (
            <CalendarEventRow
              key={`${event.type}-${event.charge_id || event.contract_id}-${event.date}`}
              event={event}
              today={today}
              showActionHint={false}
            />
          ))}
        </div>
      ) : null}
    </DashboardSection>
  );
}
