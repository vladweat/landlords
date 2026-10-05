import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { addDays, format } from 'date-fns';
import { CalendarDays } from 'lucide-react';
import { calendarApi } from '@/features/calendar/api';
import { CalendarAgenda } from '@/features/calendar/components/CalendarAgenda';
import { EmptyState } from '@/shared/ui/EmptyState';
import { ListErrorState } from '@/shared/ui/ListErrorState';
import { TableSkeleton } from '@/shared/ui/Skeleton';
import { RefreshButton } from '@/shared/ui/RefreshButton';

export default function CalendarPage() {
  const today = useMemo(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), d.getDate());
  }, []);

  const from = format(today, 'yyyy-MM-dd');
  const to = format(addDays(today, 45), 'yyyy-MM-dd');

  const { data, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: ['calendar-events', from, to],
    queryFn: () => calendarApi.getEvents({ from, to }),
  });

  const { overdue, upcoming } = useMemo(() => {
    const items = data?.items ?? [];
    const overdueItems = items.filter(
      (e) => e.type === 'charge_due' && e.status === 'overdue',
    );
    const upcomingItems = items.filter(
      (e) => !(e.type === 'charge_due' && e.status === 'overdue'),
    );
    return { overdue: overdueItems, upcoming: upcomingItems };
  }, [data]);

  const overdueTotal = useMemo(
    () =>
      overdue.reduce((sum, e) => sum + Number(e.remaining ?? e.amount ?? 0), 0),
    [overdue],
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Календарь</h1>
          <p className="text-sm text-gray-500 mt-1">
            Просрочки, ближайшие оплаты и окончания договоров
          </p>
        </div>
        <RefreshButton onClick={() => void refetch()} isLoading={isFetching} />
      </div>

      {!isLoading && !isError && overdue.length > 0 && (
        <div className="rounded-xl border border-red-100 bg-red-50 px-4 py-3">
          <p className="text-sm font-medium text-red-800">
            Просрочено: {overdue.length}{' '}
            {overdue.length === 1 ? 'начисление' : 'начислений'} на{' '}
            {overdueTotal.toLocaleString('ru-RU')} ₽
          </p>
          <p className="mt-0.5 text-xs text-red-700/80">
            Откройте событие, чтобы перейти к договору и зафиксировать платёж
          </p>
        </div>
      )}

      {isLoading ? (
        <TableSkeleton rows={6} cols={4} />
      ) : isError ? (
        <ListErrorState
          message="Не удалось загрузить календарь"
          onRetry={() => void refetch()}
          isRetrying={isFetching}
        />
      ) : !data?.items.length ? (
        <EmptyState
          icon={CalendarDays}
          title="Нет событий"
          description="Появятся просрочки, начисления к оплате и окончания активных договоров"
        />
      ) : (
        <CalendarAgenda overdue={overdue} upcoming={upcoming} today={today} />
      )}
    </div>
  );
}
