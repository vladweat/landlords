import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { addDays, format } from 'date-fns';
import { CalendarDays } from 'lucide-react';
import { calendarApi } from '@/features/calendar/api';
import { CalendarEventRow } from '@/features/calendar/components/CalendarEventRow';
import { Skeleton } from '@/shared/ui/Skeleton';
import { DashboardSection } from './DashboardSection';

const PREVIEW_LIMIT = 6;

export function UpcomingEventsWidget() {
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

  const preview = (data?.items ?? []).slice(0, PREVIEW_LIMIT);
  const total = data?.items.length ?? 0;

  return (
    <DashboardSection
      title="Ближайшие события"
      icon={<CalendarDays className="h-4 w-4 text-blue-600" />}
      action={{
        label: total > PREVIEW_LIMIT ? `Все (${total})` : 'Календарь',
        to: '/calendar',
      }}
      flush
      bodyClassName="p-0"
    >
      {isLoading ? (
        <div className="p-4 space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : isError ? (
        <div className="px-4 py-6 text-center">
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
      ) : preview.length === 0 ? (
        <div className="px-4 py-6 text-center">
          <p className="text-sm text-gray-500 mb-2">Нет ближайших событий</p>
          <Link to="/contracts" className="text-sm font-medium text-blue-600 hover:text-blue-800">
            Проверить договоры
          </Link>
        </div>
      ) : (
        <div>
          {preview.map((event) => (
            <CalendarEventRow
              key={`${event.type}-${event.charge_id || event.contract_id}-${event.date}`}
              event={event}
              today={today}
              showActionHint={false}
            />
          ))}
        </div>
      )}
    </DashboardSection>
  );
}
