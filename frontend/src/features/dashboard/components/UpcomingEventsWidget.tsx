import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { addDays, format } from 'date-fns';
import { ArrowRight, CalendarDays } from 'lucide-react';
import { calendarApi } from '@/features/calendar/api';
import { CalendarEventRow } from '@/features/calendar/components/CalendarEventRow';
import { Card } from '@/shared/ui/Card';
import { Skeleton } from '@/shared/ui/Skeleton';

const PREVIEW_LIMIT = 6;

export function UpcomingEventsWidget() {
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

  const preview = (data?.items ?? []).slice(0, PREVIEW_LIMIT);
  const total = data?.items.length ?? 0;

  return (
    <Card className="rounded-xl border border-gray-200 shadow-sm p-0 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <h2 className="text-sm font-medium text-gray-700 flex items-center gap-2">
          <CalendarDays className="h-4 w-4 text-blue-600" />
          Ближайшие события
        </h2>
        <Link
          to="/calendar"
          className="flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-800"
        >
          Все {total > PREVIEW_LIMIT ? `(${total})` : ''}
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      {isLoading ? (
        <div className="p-4 space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : isError ? (
        <p className="px-4 py-6 text-sm text-red-500">Не удалось загрузить события</p>
      ) : preview.length === 0 ? (
        <p className="px-4 py-6 text-sm text-gray-500">Нет ближайших событий</p>
      ) : (
        <div>
          {preview.map((event) => (
            <CalendarEventRow
              key={`${event.type}-${event.charge_id || event.contract_id}-${event.date}`}
              event={event}
              today={today}
            />
          ))}
        </div>
      )}
    </Card>
  );
}
