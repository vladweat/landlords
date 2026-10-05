import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/features/dashboard/api';
import { Skeleton } from '@/shared/ui/Skeleton';
import { ForecastChart } from './ForecastChart';
import { ForecastAlert } from './ForecastAlert';

export function ForecastTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-forecast'],
    queryFn: dashboardApi.getForecast,
  });

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-[160px] w-full rounded-lg" />
      </div>
    );
  }

  if (!data || (data.total_to_year_end === 0 && data.monthly_breakdown.length === 0)) {
    return (
      <div className="rounded-lg border border-dashed border-gray-200 px-3 py-6 text-center">
        <p className="text-sm text-gray-500 mb-2">Нет данных для прогноза</p>
        <Link to="/contracts" className="text-sm font-medium text-blue-600 hover:text-blue-800">
          Активируйте договор
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4">
        <span className="text-2xl font-semibold text-gray-900 tabular-nums">
          {data.total_to_year_end.toLocaleString('ru-RU')} ₽
        </span>
        <p className="text-xs text-gray-500 mt-0.5">Прогноз на основе активных контрактов</p>
      </div>
      <ForecastChart months={data.monthly_breakdown} />
      {data.alerts.length > 0 && (
        <div className="mt-4 space-y-2">
          {data.alerts.map((alert) => (
            <ForecastAlert key={alert.contract_id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}
