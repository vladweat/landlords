import { Link } from 'react-router-dom';
import { Building2 } from 'lucide-react';
import type { PropertyOverviewItem } from '@/entities/dashboard';
import { DashboardSection } from './DashboardSection';
import { shortAddress } from '@/shared/lib/address';
import { cn } from '@/shared/lib/utils';

const statusLabels: Record<string, string> = {
  active: 'Активен',
  overdue: 'Просрочка',
  vacant: 'Свободен',
};
const statusColors: Record<string, string> = {
  active: 'bg-emerald-50 text-emerald-700',
  overdue: 'bg-red-50 text-red-700',
  vacant: 'bg-gray-100 text-gray-600',
};

interface PropertiesOverviewProps {
  data: PropertyOverviewItem[];
}

function StatusBadge({ status }: { status: 'active' | 'overdue' | null }) {
  const key = status ?? 'vacant';
  return (
    <span
      className={cn(
        'inline-flex rounded-md px-1.5 py-0.5 text-[11px] font-medium shrink-0',
        statusColors[key],
      )}
    >
      {statusLabels[key]}
    </span>
  );
}

/** Компактный портфель: плотные строки вместо широкой таблицы. */
export function PropertiesOverview({ data }: PropertiesOverviewProps) {
  const sorted = [...(data || [])].sort((a, b) => {
    const rank = (s: string | null) => (s === 'overdue' ? 0 : s === null ? 2 : 1);
    return rank(a.contract_status) - rank(b.contract_status);
  });

  if (sorted.length === 0) {
    return (
      <DashboardSection
        title="Портфель"
        icon={<Building2 className="h-4 w-4 text-blue-600" />}
        action={{ label: 'Все объекты', to: '/properties' }}
      >
        <div className="py-4 text-center">
          <p className="text-sm text-gray-500 mb-3">Пока нет объектов в портфеле</p>
          <Link to="/properties" className="text-sm font-medium text-blue-600 hover:text-blue-800">
            Добавить объект
          </Link>
        </div>
      </DashboardSection>
    );
  }

  return (
    <DashboardSection
      title="Портфель"
      icon={<Building2 className="h-4 w-4 text-blue-600" />}
      action={{ label: 'Все объекты', to: '/properties' }}
      flush
      bodyClassName="p-0"
    >
      <div className="divide-y divide-gray-50">
        {sorted.map((p) => (
          <Link
            key={p.property_id}
            to={`/properties/${p.property_id}`}
            className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition-colors"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {shortAddress(p.address)}
                </p>
                <StatusBadge status={p.contract_status} />
              </div>
              <p className="text-xs text-gray-400 truncate mt-0.5">
                {p.tenant_name || 'Свободен'}
                {p.days_until_contract_end != null && p.days_until_contract_end <= 30
                  ? ` · договор через ${p.days_until_contract_end} дн.`
                  : ''}
              </p>
            </div>
            <div className="text-right flex-shrink-0">
              <p className="text-sm font-semibold text-gray-900 tabular-nums">
                {Number(p.monthly_income).toLocaleString('ru-RU')} ₽
              </p>
              {p.income_is_forecast ? (
                <p className="text-[11px] text-amber-600">прогноз</p>
              ) : (
                <p className="text-[11px] text-gray-400">/мес</p>
              )}
            </div>
          </Link>
        ))}
      </div>
    </DashboardSection>
  );
}
