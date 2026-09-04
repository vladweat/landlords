import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { addDays, format } from 'date-fns';
import { CalendarDays } from 'lucide-react';
import { calendarApi } from '@/features/calendar/api';
import { CalendarAgenda } from '@/features/calendar/components/CalendarAgenda';
import { EmptyState } from '@/shared/ui/EmptyState';
import { TableSkeleton } from '@/shared/ui/Skeleton';

export default function CalendarPage() {
  const today = useMemo(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), d.getDate());
  }, []);

  const from = format(today, 'yyyy-MM-dd');
  const to = format(addDays(today, 45), 'yyyy-MM-dd');

  const { data, isLoading, isError } = useQuery({
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Календарь</h1>
        <p className="text-sm text-gray-500 mt-1">
          Просрочки, ближайшие оплаты и окончания договоров
        </p>
      </div>

      {isLoading ? (
        <TableSkeleton rows={6} cols={4} />
      ) : isError ? (
        <p className="text-sm text-red-500">Не удалось загрузить календарь</p>
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
