import { useQuery } from '@tanstack/react-query';
import { TrendingUp } from 'lucide-react';
import { dashboardApi } from '@/features/dashboard/api';
import { Card } from '@/shared/ui/Card';
import { Skeleton } from '@/shared/ui/Skeleton';
import { ForecastChart } from './ForecastChart';
import { ForecastAlert } from './ForecastAlert';

export function ForecastWidget() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard-forecast'],
    queryFn: dashboardApi.getForecast,
  });

  if (isLoading) {
    return (
      <Card className="rounded-xl border border-gray-200 shadow-sm">
        <Skeleton className="h-5 w-48 mb-4" />
        <Skeleton className="h-8 w-32 mb-4" />
        <Skeleton className="h-[220px] w-full rounded-lg" />
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className="rounded-xl border border-gray-200 shadow-sm">
        <h2 className="text-lg font-medium text-gray-800 mb-4 flex items-center gap-2"><TrendingUp className="h-5 w-5" /> Прогноз дохода</h2>
        <p className="text-sm text-red-500">Ошибка загрузки прогноза</p>
      </Card>
    );
  }

  if (data.total_to_year_end === 0 && data.monthly_breakdown.length === 0) {
    return (
      <Card className="rounded-xl border border-gray-200 shadow-sm">
        <h2 className="text-lg font-medium text-gray-800 mb-4 flex items-center gap-2"><TrendingUp className="h-5 w-5" /> Прогноз дохода</h2>
        <p className="text-sm text-gray-500">Нет активных контрактов для прогноза</p>
      </Card>
    );
  }

  return (
    <Card className="rounded-xl border border-gray-200 shadow-sm p-5">
      <h2 className="text-lg font-medium text-gray-800 mb-4 flex items-center gap-2"><TrendingUp className="h-5 w-5" /> Прогноз дохода до конца года</h2>
      <p className="text-3xl font-bold text-gray-900 mb-1">{data.total_to_year_end.toLocaleString('ru-RU')} ₽</p>
      <p className="text-sm text-gray-500 mb-4">ожидаемый доход до 31 декабря 2026</p>
      <ForecastChart months={data.monthly_breakdown} />
      {data.alerts.length > 0 && (
        <div className="mt-4 space-y-2">
          {data.alerts.map((alert) => (
            <ForecastAlert key={alert.contract_id} alert={alert} />
          ))}
        </div>
      )}
    </Card>
  );
}
