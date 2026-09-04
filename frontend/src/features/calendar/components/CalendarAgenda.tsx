import type { CalendarEvent } from '@/entities/calendar';
import { CalendarEventRow } from './CalendarEventRow';
import { formatDate, parseLocalDate } from '@/shared/lib/utils';

interface CalendarAgendaProps {
  overdue: CalendarEvent[];
  upcoming: CalendarEvent[];
  today: Date;
}

function groupByDate(events: CalendarEvent[]): { date: string; items: CalendarEvent[] }[] {
  const map = new Map<string, CalendarEvent[]>();
  for (const event of events) {
    const key = event.date;
    const list = map.get(key) || [];
    list.push(event);
    map.set(key, list);
  }
  return Array.from(map.entries()).map(([date, items]) => ({ date, items }));
}

export function CalendarAgenda({ overdue, upcoming, today }: CalendarAgendaProps) {
  const groups = groupByDate(upcoming);

  return (
    <div className="space-y-6">
      {overdue.length > 0 && (
        <section>
          <h2 className="text-sm font-medium text-red-700 mb-2 px-1">
            Просрочки ({overdue.length})
          </h2>
          <div className="overflow-hidden rounded-xl border border-red-100 bg-white">
            {overdue.map((event) => (
              <CalendarEventRow
                key={`${event.type}-${event.charge_id || event.contract_id}-${event.date}`}
                event={event}
                today={today}
              />
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="text-sm font-medium text-gray-700 mb-2 px-1">Ближайшие 45 дней</h2>
        {groups.length === 0 ? (
          <div className="rounded-xl border border-gray-100 bg-white px-4 py-8 text-center text-sm text-gray-500">
            Нет событий в ближайшие 45 дней
          </div>
        ) : (
          <div className="space-y-4">
            {groups.map(({ date, items }) => (
              <div key={date}>
                <p className="text-xs font-medium uppercase tracking-wide text-gray-400 mb-1 px-1">
                  {formatDate(parseLocalDate(date), 'EEEE, d MMMM')}
                </p>
                <div className="overflow-hidden rounded-xl border border-gray-100 bg-white">
                  {items.map((event) => (
                    <CalendarEventRow
                      key={`${event.type}-${event.charge_id || event.contract_id}-${event.date}`}
                      event={event}
                      today={today}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
