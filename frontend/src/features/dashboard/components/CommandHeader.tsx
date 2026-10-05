import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  Building2,
  FileText,
  Percent,
  Scale,
  TrendingDown,
  TrendingUp,
  type LucideIcon,
} from 'lucide-react';
import type { DashboardSummary } from '@/entities/dashboard';
import { useCountUp } from '@/shared/hooks/useCountUp';
import { RefreshButton } from '@/shared/ui/RefreshButton';
import { QuickActions } from './QuickActions';
import { cn } from '@/shared/lib/utils';

function AnimatedNumber({ value, format = false }: { value: number; format?: boolean }) {
  const counted = useCountUp(value, 800);
  return <>{format ? counted.toLocaleString('ru-RU') : counted}</>;
}

interface CommandHeaderProps {
  greetingText: string;
  greetingIcon: LucideIcon;
  subtitle: string;
  summary: DashboardSummary;
  overdueContractsCount: number;
  showFinance: boolean;
  onRefresh: () => void;
  isRefreshing: boolean;
}

/** Единая шапка-сводка: приветствие, главный KPI месяца и вторичные метрики. */
export function CommandHeader({
  greetingText,
  greetingIcon: GreetingIcon,
  subtitle,
  summary,
  overdueContractsCount,
  showFinance,
  onRefresh,
  isRefreshing,
}: CommandHeaderProps) {
  const collected = Number(summary.monthly_collected_income);
  const expected = Number(summary.monthly_expected_income);
  const remaining = Math.max(0, expected - collected);
  const progress =
    expected > 0 ? Math.min(100, Math.round((collected / expected) * 100)) : collected > 0 ? 100 : 0;
  const changePercent = summary.monthly_income_change_percent ?? 0;
  const isZero = changePercent === 0;
  const isPositive = changePercent > 0;
  const occupancy = Math.round(summary.occupancy_rate ?? 0);
  const outstanding = Number(summary.outstanding_balance || 0);

  return (
    <div className="rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      <div className="px-4 sm:px-5 pt-4 pb-3 flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 flex-shrink-0">
            <GreetingIcon className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <p className="text-lg font-semibold text-gray-900 truncate">{greetingText}</p>
            <p className="text-xs text-gray-500">{subtitle}</p>
          </div>
        </div>
        <RefreshButton onClick={onRefresh} isLoading={isRefreshing} />
      </div>

      <div className="px-4 sm:px-5 pb-3">
        <QuickActions compact />
      </div>

      <div className="border-t border-gray-100 px-4 sm:px-5 py-4">
        {showFinance ? (
          <div className="flex flex-col lg:flex-row lg:items-end gap-5">
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-1">
                Сбор за месяц
              </p>
              <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                <Link
                  to="/payments"
                  className="text-2xl sm:text-3xl font-semibold text-gray-900 tabular-nums hover:text-blue-700"
                >
                  <AnimatedNumber value={collected} format /> ₽
                </Link>
                <span className="text-sm text-gray-400 tabular-nums">
                  из {expected.toLocaleString('ru-RU')} ₽
                </span>
                {!isZero && (
                  <span
                    className={cn(
                      'text-xs font-medium inline-flex items-center gap-0.5',
                      isPositive ? 'text-emerald-600' : 'text-red-500',
                    )}
                  >
                    {isPositive ? (
                      <TrendingUp className="h-3 w-3" />
                    ) : (
                      <TrendingDown className="h-3 w-3" />
                    )}
                    {isPositive ? '+' : '−'}
                    {Math.abs(changePercent).toFixed(1)}%
                  </span>
                )}
              </div>
              <div className="mt-3 h-2 rounded-full bg-gray-100 overflow-hidden max-w-xl">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="mt-1.5 text-xs text-gray-500 tabular-nums">
                Осталось собрать {remaining.toLocaleString('ru-RU')} ₽
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-px rounded-xl border border-gray-200 bg-gray-200 overflow-hidden lg:min-w-[22rem]">
              <MetricCell
                to="/properties"
                icon={Building2}
                label="Объекты"
                value={String(summary.active_properties)}
              />
              <MetricCell
                to="/contracts?status=active"
                icon={FileText}
                label="Договоры"
                value={String(summary.active_contracts)}
                hint={
                  overdueContractsCount > 0 ? (
                    <span className="text-red-600">{overdueContractsCount} проср.</span>
                  ) : undefined
                }
              />
              <MetricCell
                to="/properties"
                icon={Percent}
                label="Занятость"
                value={`${occupancy}%`}
              />
              <MetricCell
                to="/calendar"
                icon={Scale}
                label="К получению"
                value={`${outstanding.toLocaleString('ru-RU')} ₽`}
              />
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-px rounded-xl border border-gray-200 bg-gray-200 overflow-hidden">
            <MetricCell
              to="/properties"
              icon={Building2}
              label="Объекты"
              value={String(summary.active_properties)}
            />
            <MetricCell
              to="/contracts?status=active"
              icon={FileText}
              label="Договоры"
              value={String(summary.active_contracts)}
            />
            <MetricCell to="/properties" icon={Percent} label="Занятость" value={`${occupancy}%`} />
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCell({
  to,
  icon: Icon,
  label,
  value,
  hint,
}: {
  to: string;
  icon: LucideIcon;
  label: string;
  value: string;
  hint?: ReactNode;
}) {
  return (
    <Link to={to} className="bg-white px-3 py-2.5 hover:bg-gray-50 transition-colors">
      <div className="flex items-center gap-1 text-[11px] text-gray-500 mb-0.5">
        <Icon className="h-3 w-3 text-gray-400" />
        {label}
      </div>
      <p className="text-sm font-semibold text-gray-900 tabular-nums truncate">{value}</p>
      {hint ? <p className="text-[11px] mt-0.5 truncate">{hint}</p> : null}
    </Link>
  );
}
