import { Link } from 'react-router-dom';
import { Building2 } from 'lucide-react';
import type { PropertyOverviewItem } from '@/entities/dashboard';
import { DashboardSection } from './DashboardSection';
import { shortAddress } from '@/shared/lib/address';

const statusLabels: Record<string, string> = {
  active: 'Активен',
  overdue: 'Просрочка',
  vacant: 'Свободен',
};
const statusColors: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  overdue: 'bg-red-100 text-red-700',
  vacant: 'bg-gray-100 text-gray-600',
};

interface PropertiesOverviewProps {
  data: PropertyOverviewItem[];
}

function StatusBadge({ status }: { status: 'active' | 'overdue' | null }) {
  const key = status ?? 'vacant';
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[key]}`}
    >
      {statusLabels[key]}
    </span>
  );
}

export function PropertiesOverview({ data }: PropertiesOverviewProps) {
  if (!data || data.length === 0) {
    return (
      <DashboardSection
        title="Объекты"
        icon={<Building2 className="h-4 w-4 text-blue-600" />}
        action={{ label: 'Все объекты', to: '/properties' }}
      >
        <div className="py-4 text-center">
          <p className="text-sm text-gray-500 mb-3">Пока нет объектов в портфеле</p>
          <Link
            to="/properties"
            className="text-sm font-medium text-blue-600 hover:text-blue-800"
          >
            Добавить объект
          </Link>
        </div>
      </DashboardSection>
    );
  }

  return (
    <DashboardSection
      title="Объекты"
      icon={<Building2 className="h-4 w-4 text-blue-600" />}
      action={{ label: 'Все объекты', to: '/properties' }}
      bodyClassName="p-0"
      flush
    >
      <div className="hidden sm:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-left text-gray-500">
              <th className="px-4 py-2.5 font-medium">Объект</th>
              <th className="px-4 py-2.5 font-medium">Арендатор</th>
              <th className="px-4 py-2.5 font-medium">Статус</th>
              <th className="px-4 py-2.5 font-medium text-right">Доход/мес</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {data.map((p) => (
              <tr key={p.property_id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-2.5 font-medium truncate max-w-[220px]">
                  <Link
                    to={`/properties/${p.property_id}`}
                    className="text-gray-900 hover:text-blue-700"
                  >
                    {shortAddress(p.address)}
                  </Link>
                </td>
                <td className="px-4 py-2.5 text-gray-500">
                  {p.tenant_name || <span className="text-gray-300">—</span>}
                </td>
                <td className="px-4 py-2.5">
                  <StatusBadge status={p.contract_status} />
                </td>
                <td className="px-4 py-2.5 text-right font-medium tabular-nums">
                  {Number(p.monthly_income).toLocaleString('ru-RU')} ₽
                  {p.income_is_forecast ? (
                    <span className="ml-1 text-[11px] font-normal text-amber-600">прогноз</span>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="sm:hidden divide-y divide-gray-50">
        {data.map((p) => (
          <Link
            key={p.property_id}
            to={`/properties/${p.property_id}`}
            className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-gray-50"
          >
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {shortAddress(p.address)}
              </p>
              <div className="mt-1 flex items-center gap-2">
                <StatusBadge status={p.contract_status} />
                <span className="text-xs text-gray-400 truncate">
                  {p.tenant_name || 'Свободен'}
                </span>
              </div>
            </div>
            <span className="text-sm font-semibold tabular-nums flex-shrink-0">
              {Number(p.monthly_income).toLocaleString('ru-RU')} ₽
            </span>
          </Link>
        ))}
      </div>
    </DashboardSection>
  );
}
