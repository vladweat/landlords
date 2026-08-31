import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/features/dashboard/api';
import { Skeleton } from '@/shared/ui/Skeleton';
import { ForecastChart } from './ForecastChart';
import { ForecastAlert } from './ForecastAlert';

export function ForecastTab() {
  const { data, isLoading } = useQuery({ queryKey: ['dashboard-forecast'], queryFn: dashboardApi.getForecast });

  if (isLoading) return <div className="space-y-3"><Skeleton className="h-5 w-48" /><Skeleton className="h-8 w-32" /><Skeleton className="h-[160px] w-full rounded-lg" /></div>;
  if (!data || (data.total_to_year_end === 0 && data.monthly_breakdown.length === 0)) return <p className="text-sm text-gray-500">Нет данных для прогноза</p>;

  return (
    <div>
      <div className="mb-4">
        <span className="text-2xl font-semibold text-gray-900">{data.total_to_year_end.toLocaleString('ru-RU')} ₽</span>
        <p className="text-xs text-gray-500 mt-0.5">Прогноз на основе активных контрактов</p>
      </div>
      <ForecastChart months={data.monthly_breakdown} />
      {data.alerts.length > 0 && (
        <div className="mt-4 space-y-2">
          {data.alerts.map((alert) => <ForecastAlert key={alert.contract_id} alert={alert} />)}
        </div>
      )}
    </div>
  );
}
