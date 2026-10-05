import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  Building2,
  FileText,
  Wallet,
  Percent,
  Scale,
  TrendingUp,
  TrendingDown,
  type LucideIcon,
} from 'lucide-react';
import type { DashboardSummary } from '@/entities/dashboard';
import { useCountUp } from '@/shared/hooks/useCountUp';
import { cn } from '@/shared/lib/utils';

function AnimatedNumber({ value, format = false }: { value: number; format?: boolean }) {
  const counted = useCountUp(value, 800);
  return <>{format ? counted.toLocaleString('ru-RU') : counted}</>;
}

interface KpiTileProps {
  to: string;
  title: string;
  icon: LucideIcon;
  iconClass: string;
  value: ReactNode;
  hint?: ReactNode;
  accent?: boolean;
}

function KpiTile({ to, title, icon: Icon, iconClass, value, hint, accent }: KpiTileProps) {
  return (
    <Link
      to={to}
      className={cn(
        'rounded-xl border bg-white px-3.5 py-3 shadow-sm transition-colors hover:border-gray-300',
        accent ? 'border-blue-200 bg-blue-50/40' : 'border-gray-200',
      )}
    >
      <div className="flex items-center gap-1.5 text-xs text-gray-500 mb-1.5">
        <Icon className={cn('h-3.5 w-3.5', iconClass)} />
        <span>{title}</span>
      </div>
      <div className="text-base font-semibold text-gray-900 tabular-nums">{value}</div>
      {hint ? <div className="mt-1 text-xs text-gray-500">{hint}</div> : null}
    </Link>
  );
}

interface DashboardKpiBarProps {
  summary: DashboardSummary;
  overdueContractsCount: number;
  showFinance: boolean;
}

export function DashboardKpiBar({ summary, overdueContractsCount, showFinance }: DashboardKpiBarProps) {
  const collected = Number(summary.monthly_collected_income);
  const expected = Number(summary.monthly_expected_income);
  const remaining = Math.max(0, expected - collected);
  const changePercent = summary.monthly_income_change_percent ?? 0;
  const isZero = changePercent === 0;
  const isPositive = changePercent > 0;
  const occupancy = Math.round(summary.occupancy_rate ?? 0);
  const outstanding = Number(summary.outstanding_balance || 0);

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
      <KpiTile
        to="/properties"
        title="Объекты"
        icon={Building2}
        iconClass="text-blue-600"
        value={<AnimatedNumber value={summary.active_properties} />}
      />
      <KpiTile
        to="/contracts?status=active"
        title="Договоры"
        icon={FileText}
        iconClass="text-emerald-600"
        value={<AnimatedNumber value={summary.active_contracts} />}
        hint={
          overdueContractsCount > 0 ? (
            <span className="text-red-600">{overdueContractsCount} с просрочкой</span>
          ) : (
            'активные'
          )
        }
      />
      <KpiTile
        to="/properties"
        title="Занятость"
        icon={Percent}
        iconClass="text-violet-600"
        value={<>{occupancy}%</>}
      />
      {showFinance && (
        <>
          <KpiTile
            to="/payments"
            title="Получено за месяц"
            icon={Wallet}
            iconClass="text-amber-600"
            accent
            value={
              <>
                <AnimatedNumber value={collected} format /> ₽
              </>
            }
            hint={
              !isZero ? (
                <span className={cn(isPositive ? 'text-emerald-600' : 'text-red-500')}>
                  {isPositive ? (
                    <TrendingUp className="h-3 w-3 inline mr-0.5" />
                  ) : (
                    <TrendingDown className="h-3 w-3 inline mr-0.5" />
                  )}
                  {isPositive ? '+' : '−'}
                  {Math.abs(changePercent).toFixed(1)}% к прошлому месяцу
                </span>
              ) : (
                <>из {expected.toLocaleString('ru-RU')} ₽ ожидаемых</>
              )
            }
          />
          <KpiTile
            to="/payments"
            title="Осталось собрать"
            icon={Wallet}
            iconClass="text-sky-600"
            value={<>{remaining.toLocaleString('ru-RU')} ₽</>}
          />
          <KpiTile
            to="/calendar"
            title="К получению"
            icon={Scale}
            iconClass="text-rose-600"
            value={<>{outstanding.toLocaleString('ru-RU')} ₽</>}
            hint="баланс по начислениям"
          />
        </>
      )}
    </div>
  );
}
