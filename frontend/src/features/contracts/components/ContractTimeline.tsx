import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { contractsApi } from '@/features/contracts/api';
import { Button } from '@/shared/ui/Button';
import { Skeleton } from '@/shared/ui/Skeleton';
import { TimelineItem } from './TimelineItem';
import { AddNoteForm } from './AddNoteForm';

interface ContractTimelineProps {
  contractId: string;
}

export function ContractTimeline({ contractId }: ContractTimelineProps) {
  const [page, setPage] = useState(1);
  const perPage = 10;

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['contract-events', contractId, page],
    queryFn: () => contractsApi.getEvents(contractId, page, perPage),
  });

  const events = data?.items || [];
  const hasMore = data ? data.page < data.pages : false;

  return (
    <div>
      <AddNoteForm contractId={contractId} />

      {isLoading ? (
        <div className="space-y-3">
          {[1,2,3,4].map((i) => (
            <div key={i} className="flex gap-4 py-3">
              <Skeleton className="h-9 w-9 rounded-full flex-shrink-0" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-48" />
              </div>
            </div>
          ))}
        </div>
      ) : events.length === 0 ? (
        <p className="text-sm text-gray-500 py-4 text-center">История пуста. Добавьте первую заметку.</p>
      ) : (
        <>
          <div className="divide-y divide-gray-100">
            {events.map((event) => (
              <TimelineItem key={event.id} {...event} />
            ))}
          </div>
          {hasMore && (
            <div className="text-center mt-4">
              <Button variant="ghost" size="sm" onClick={() => setPage(p => p + 1)} isLoading={isFetching}>
                Загрузить ещё
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
