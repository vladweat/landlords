import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { contractsApi } from '@/features/contracts/api';
import { useCan } from '@/features/auth/permissions';
import type { ContractEvent } from '@/entities/contract';
import { Button } from '@/shared/ui/Button';
import { Skeleton } from '@/shared/ui/Skeleton';
import { TimelineItem } from './TimelineItem';
import { AddNoteForm } from './AddNoteForm';

interface ContractTimelineProps {
  contractId: string;
}

export function ContractTimeline({ contractId }: ContractTimelineProps) {
  const canWrite = useCan('write_contracts');
  const [page, setPage] = useState(1);
  const [accumulated, setAccumulated] = useState<ContractEvent[]>([]);
  const perPage = 10;

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['contract-events', contractId, page],
    queryFn: () => contractsApi.getEvents(contractId, page, perPage),
  });

  useEffect(() => {
    setPage(1);
    setAccumulated([]);
  }, [contractId]);

  useEffect(() => {
    if (!data) return;
    setAccumulated((prev) => {
      if (data.page === 1) return data.items;
      const seen = new Set(prev.map((e) => e.id));
      const next = data.items.filter((e) => !seen.has(e.id));
      return [...prev, ...next];
    });
  }, [data]);

  const events = accumulated;
  const hasMore = data ? data.page < data.pages : false;

  return (
    <div className="space-y-5">
      {canWrite && <AddNoteForm contractId={contractId} />}

      {isLoading && events.length === 0 ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex gap-4">
              <Skeleton className="h-9 w-9 rounded-full shrink-0" />
              <div className="flex-1 space-y-2 pt-1">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-3 w-64" />
              </div>
            </div>
          ))}
        </div>
      ) : events.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-500">
          Пока нет событий.
          {canWrite
            ? ' Добавьте заметку выше — здесь также появятся платежи и смены статуса.'
            : ' Здесь появятся платежи и смены статуса.'}
        </p>
      ) : (
        <div>
          {events.map((event, index) => (
            <TimelineItem
              key={event.id}
              {...event}
              isLast={index === events.length - 1 && !hasMore}
            />
          ))}
          {hasMore && (
            <div className="pl-12">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                isLoading={isFetching}
              >
                Загрузить ещё
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
