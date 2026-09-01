import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Building2, CreditCard, Wallet, AlertTriangle, TrendingUp, TrendingDown, Sun, Moon, Sunset } from 'lucide-react';
import { dashboardApi } from '@/features/dashboard/api';
import { AnalyticsWidget } from '@/features/dashboard/components/AnalyticsWidget';
import { PropertiesOverview } from '@/features/dashboard/components/PropertiesOverview';
import { OverdueAlert } from '@/features/dashboard/components/OverdueAlert';
import { OnboardingWizard } from '@/features/onboarding/OnboardingWizard';
import { Card } from '@/shared/ui/Card';
import { Skeleton } from '@/shared/ui/Skeleton';
import { RefreshButton } from '@/shared/ui/RefreshButton';
import { useAuthStore } from '@/features/auth/store';
import { isOnboardingCompleted } from '@/shared/lib/onboarding';
import { useHotkeys } from '@/shared/hooks/useHotkeys';
import { useCountUp } from '@/shared/hooks/useCountUp';
import { cn } from '@/shared/lib/utils';

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 6) return { text: 'Доброй ночи', Icon: Moon };
  if (hour < 12) return { text: 'Доброе утро', Icon: Sun };
  if (hour < 18) return { text: 'Добрый день', Icon: Sun };
  return { text: 'Добрый вечер', Icon: Sunset };
}

const fadeUp = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

function AnimatedNumber({ value, format = false }: { value: number; format?: boolean }) {
  const counted = useCountUp(value, 800);
  return <>{format ? counted.toLocaleString('ru-RU') : counted}</>;
}

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [showOnboarding, setShowOnboarding] = useState(!isOnboardingCompleted());
  const user = useAuthStore((s) => s.user);

  const summaryQuery = useQuery({ queryKey: ['dashboard-summary'], queryFn: dashboardApi.getSummary });
  const lastPaymentsQuery = useQuery({ queryKey: ['dashboard-last-payments'], queryFn: () => dashboardApi.getLastPayments(5) });

  useHotkeys({ r: () => { queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] }); queryClient.invalidateQueries({ queryKey: ['dashboard-last-payments'] }); } });

  const summary = summaryQuery.data;
  const lastPayments = lastPaymentsQuery.data ?? [];
  const overdueCount = useMemo(() => (summary?.properties_overview || []).filter(p => p.contract_status === 'overdue').length, [summary]);
  const changePercent = summary?.monthly_income_change_percent ?? 0;
  const isZero = changePercent === 0;
  const isPositive = changePercent > 0;
  const showOnboardingNow = showOnboarding && (summary?.active_properties ?? 0) === 0 && (summary?.active_contracts ?? 0) === 0;
  const invalidateAll = () => { queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] }); queryClient.invalidateQueries({ queryKey: ['dashboard-last-payments'] }); };
  const greeting = useMemo(() => getGreeting(), []);

  if (summaryQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4"><Skeleton className="h-64 rounded-xl lg:col-span-2" /><Skeleton className="h-64 rounded-xl" /></div>
      </div>
    );
  }

  if (summaryQuery.isError || !summary) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertTriangle className="h-10 w-10 text-red-400 mb-3" />
        <p className="text-red-500 mb-4">Не удалось загрузить данные</p>
        <RefreshButton onClick={invalidateAll} isLoading={false} />
      </div>
    );
  }

  const GreetingIcon = greeting.Icon;

  return (
    <motion.div initial="hidden" animate="show" className="space-y-4">
      {/* Header: Greeting + KPI inline */}
      <motion.div variants={fadeUp} className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600 flex-shrink-0">
            <GreetingIcon className="h-4 w-4" />
          </div>
          <div>
            <p className="text-base font-medium text-gray-900">
              {greeting.text}{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}
            </p>
            <p className="text-xs text-gray-500">
              {(summary.active_contracts ) > 0 
                ? `${(summary.active_contracts )} активных договоров · доход ${Number(summary.monthly_collected_income).toLocaleString('ru-RU')} ₽` 
                : 'Добавьте первый объект, чтобы начать'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-5 text-sm">
          <Link to="/properties" className="flex items-center gap-1.5 text-gray-600 hover:text-gray-900"><Building2 className="h-4 w-4 text-blue-600" /><span className="font-medium"><AnimatedNumber value={summary.active_properties} /></span></Link>
          <Link to="/contracts?status=active" className="flex items-center gap-1.5 text-gray-600 hover:text-gray-900"><CreditCard className="h-4 w-4 text-emerald-600" /><span className="font-medium"><AnimatedNumber value={(summary.active_contracts)} /></span></Link>
          <Link to="/contracts?status=overdue" className={cn('flex items-center gap-1.5', overdueCount > 0 ? 'text-red-600' : 'text-gray-600 hover:text-gray-900')}><AlertTriangle className="h-4 w-4" /><span className="font-medium"><AnimatedNumber value={overdueCount} /></span></Link>
          <Link to="/payments" className="flex items-center gap-1.5 text-gray-600 hover:text-gray-900"><Wallet className="h-4 w-4 text-amber-600" /><span className="font-medium"><AnimatedNumber value={Number(summary.monthly_collected_income)} format /> ₽</span>{!isZero && <span className={cn('text-xs', isPositive ? 'text-emerald-600' : 'text-red-500')}>{isPositive ? <TrendingUp className="h-3 w-3 inline" /> : <TrendingDown className="h-3 w-3 inline" />}{isPositive ? '+' : '-'}{Math.abs(changePercent).toFixed(1)}%</span>}</Link>
          <RefreshButton onClick={invalidateAll} isLoading={summaryQuery.isFetching} />
        </div>
      </motion.div>

      {showOnboardingNow && <motion.div variants={fadeUp}><OnboardingWizard onComplete={() => setShowOnboarding(false)} /></motion.div>}
      <motion.div variants={fadeUp}><OverdueAlert count={overdueCount} amount={summary.overdue_total_amount || '0'} /></motion.div>

      <motion.div variants={fadeUp}><AnalyticsWidget /></motion.div>
      <motion.div variants={fadeUp}><PropertiesOverview data={summary.properties_overview || []} /></motion.div>

      <motion.div variants={fadeUp}>
        <Card className="rounded-xl border border-gray-200 shadow-sm p-4">
          <h2 className="text-sm font-medium text-gray-700 mb-3">Последние платежи</h2>
          {lastPayments.length === 0 ? <p className="text-sm text-gray-500">Платежей пока нет</p> : (
            <div className="flex flex-wrap gap-4">
              {lastPayments.slice(0, 5).map((p) => (
                <div key={p.id} className="flex items-center gap-2 text-sm">
                  <span className="text-gray-900 font-medium">{p.tenant_name}</span>
                  <span className="text-gray-400">—</span>
                  <span className="text-emerald-600 font-medium">+{Number(p.amount).toLocaleString('ru-RU')} ₽</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </motion.div>
    </motion.div>
  );
}
