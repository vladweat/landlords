import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { apiClient } from '@/shared/api/client';
import { FullPageLoader } from '@/shared/ui/FullPageLoader';

type Overall = 'operational' | 'degraded' | 'outage';

interface Incident {
  id: string;
  title: string;
  status: string;
  started_at: string;
  resolved_at?: string | null;
  message?: string | null;
}

interface PublicStatus {
  overall: Overall;
  updated_at: string;
  support_email: string;
  status_url?: string;
  incidents: Incident[];
}

const OVERALL_LABEL: Record<Overall, string> = {
  operational: 'Все системы работают',
  degraded: 'Частичные проблемы',
  outage: 'Сервис недоступен',
};

const OVERALL_CLASS: Record<Overall, string> = {
  operational: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  degraded: 'bg-amber-50 text-amber-900 border-amber-200',
  outage: 'bg-red-50 text-red-800 border-red-200',
};

async function fetchStatus(): Promise<PublicStatus> {
  const response = await apiClient.get<{ status: string; data: PublicStatus }>(
    '/public/status',
  );
  return response.data.data;
}

function formatDt(value: string | null | undefined): string {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString('ru-RU', { dateStyle: 'medium', timeStyle: 'short' });
}

export default function StatusPage() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['public-status'],
    queryFn: fetchStatus,
    refetchInterval: 60_000,
  });

  if (isLoading) return <FullPageLoader />;

  const overall = data?.overall ?? 'degraded';

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-10">
      <div className="mx-auto max-w-2xl">
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <Link to="/" className="text-sm text-blue-600 hover:underline">
              ← Landlords
            </Link>
            <h1 className="mt-2 text-3xl font-semibold text-gray-900">Статус сервиса</h1>
            <p className="mt-1 text-sm text-gray-500">
              Обновлено: {formatDt(data?.updated_at)}
            </p>
          </div>
          <button
            type="button"
            onClick={() => void refetch()}
            className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
            disabled={isFetching}
          >
            Обновить
          </button>
        </div>

        {isError || !data ? (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-amber-900">
            Не удалось загрузить статус. Напишите на{' '}
            <a href="mailto:hello@landlords.ru" className="underline">
              hello@landlords.ru
            </a>
            .
          </div>
        ) : (
          <>
            <div
              className={`rounded-xl border px-5 py-4 text-lg font-medium ${OVERALL_CLASS[overall]}`}
            >
              {OVERALL_LABEL[overall]}
            </div>

            <section className="mt-8">
              <h2 className="text-lg font-medium text-gray-900 mb-3">Инциденты</h2>
              {data.incidents.length === 0 ? (
                <p className="text-sm text-gray-500">Активных инцидентов нет.</p>
              ) : (
                <ul className="space-y-3">
                  {data.incidents.map((inc) => (
                    <li
                      key={inc.id}
                      className="rounded-xl border border-gray-200 bg-white p-4"
                    >
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <h3 className="font-medium text-gray-900">{inc.title}</h3>
                        <span className="text-xs uppercase tracking-wide text-gray-500">
                          {inc.status}
                        </span>
                      </div>
                      {inc.message && (
                        <p className="mt-2 text-sm text-gray-600">{inc.message}</p>
                      )}
                      <p className="mt-2 text-xs text-gray-400">
                        Начало: {formatDt(inc.started_at)}
                        {inc.resolved_at
                          ? ` · Закрыт: ${formatDt(inc.resolved_at)}`
                          : ''}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <p className="mt-10 text-sm text-gray-500">
              Поддержка:{' '}
              <a
                href={`mailto:${data.support_email || 'hello@landlords.ru'}`}
                className="text-blue-600 hover:underline"
              >
                {data.support_email || 'hello@landlords.ru'}
              </a>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
