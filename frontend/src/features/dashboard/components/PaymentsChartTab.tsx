import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowUpRight } from 'lucide-react';
import { dashboardApi } from '@/features/dashboard/api';
import { Skeleton } from '@/shared/ui/Skeleton';
import { formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';
import { parseLocalDate } from '@/shared/lib/utils';
import { shortAddress } from '@/shared/lib/address';

export function PaymentsChartTab() {
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: dashboardApi.getSummary,
  });
  const {
    data: payments,
    isLoading: paymentsLoading,
    isError: paymentsError,
  } = useQuery({
    queryKey: ['dashboard-last-payments'],
    queryFn: () => dashboardApi.getLastPayments(10),
  });

  if (summaryLoading || paymentsLoading) {
    return <Skeleton className="h-[200px] w-full rounded-lg" />;
  }
  if (!summary) {
    return <p className="text-sm text-gray-500">Нет данных</p>;
  }

  const expected = Number(summary.monthly_expected_income);
  const collected = Number(summary.monthly_collected_income);
  const remaining = Math.max(0, expected - collected);

  return (
    <div>
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500">Осталось получить</p>
          <p className="text-sm font-semibold tabular-nums">{remaining.toLocaleString('ru-RU')} ₽</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500">Получено</p>
          <p className="text-sm font-semibold text-emerald-600 tabular-nums">
            {collected.toLocaleString('ru-RU')} ₽
          </p>
        </div>
      </div>

      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide">
          Последние поступления
        </h3>
        <Link to="/payments" className="text-xs font-medium text-blue-600 hover:text-blue-800">
          Все платежи
        </Link>
      </div>

      {paymentsError ? (
        <p className="text-sm text-red-500">Не удалось загрузить платежи</p>
      ) : !payments || payments.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-200 px-3 py-6 text-center">
          <p className="text-sm text-gray-500 mb-2">Платежей пока нет</p>
          <Link to="/payments" className="text-sm font-medium text-blue-600 hover:text-blue-800">
            Записать первый платёж
          </Link>
        </div>
      ) : (
        <div className="space-y-1">
          {payments.slice(0, 7).map((p) => {
            const relativeTime = p.date_paid
              ? formatDistanceToNow(parseLocalDate(p.date_paid), {
                  addSuffix: true,
                  locale: ru,
                })
              : '';
            return (
              <Link
                key={p.id}
                to={`/contracts/${p.contract_id}`}
                className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <ArrowUpRight className="h-4 w-4 text-emerald-500 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm text-gray-900 truncate">
                      {shortAddress(p.property_address)}
                    </p>
                    <p className="text-xs text-gray-400">
                      {p.tenant_name}
                      {relativeTime ? ` · ${relativeTime}` : ''}
                    </p>
                  </div>
                </div>
                <span className="text-sm font-medium text-emerald-600 flex-shrink-0 ml-3 tabular-nums">
                  +{Number(p.amount).toLocaleString('ru-RU')} ₽
                </span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
