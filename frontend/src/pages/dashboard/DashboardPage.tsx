import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Sun, Moon, Sunset } from 'lucide-react';
import { dashboardApi } from '@/features/dashboard/api';
import { AnalyticsWidget } from '@/features/dashboard/components/AnalyticsWidget';
import { PropertiesOverview } from '@/features/dashboard/components/PropertiesOverview';
import { UpcomingEventsWidget } from '@/features/dashboard/components/UpcomingEventsWidget';
import { DashboardKpiBar } from '@/features/dashboard/components/DashboardKpiBar';
import { AttentionPanel } from '@/features/dashboard/components/AttentionPanel';
import { QuickActions } from '@/features/dashboard/components/QuickActions';
import { OnboardingWizard } from '@/features/onboarding/OnboardingWizard';
import { Skeleton } from '@/shared/ui/Skeleton';
import { RefreshButton } from '@/shared/ui/RefreshButton';
import { ListErrorState } from '@/shared/ui/ListErrorState';
import { useAuthStore } from '@/features/auth/store';
import { isOnboardingCompleted } from '@/shared/lib/onboarding';
import { useHotkeys } from '@/shared/hooks/useHotkeys';

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 6) return { text: 'Доброй ночи', Icon: Moon };
  if (hour < 12) return { text: 'Доброе утро', Icon: Sun };
  if (hour < 18) return { text: 'Добрый день', Icon: Sun };
  return { text: 'Добрый вечер', Icon: Sunset };
}

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

function invalidateDashboard(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
  queryClient.invalidateQueries({ queryKey: ['dashboard-last-payments'] });
  queryClient.invalidateQueries({ queryKey: ['dashboard-forecast'] });
  queryClient.invalidateQueries({ queryKey: ['calendar-events'] });
}

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [showOnboarding, setShowOnboarding] = useState(!isOnboardingCompleted());
  const user = useAuthStore((s) => s.user);
  const role = useAuthStore((s) => s.role);

  const summaryQuery = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: dashboardApi.getSummary,
  });

  useHotkeys({
    r: () => invalidateDashboard(queryClient),
  });

  const summary = summaryQuery.data;
  const overdueContractsCount = useMemo(
    () => (summary?.properties_overview || []).filter((p) => p.contract_status === 'overdue').length,
    [summary],
  );

  const showOnboardingNow =
    showOnboarding &&
    (summary?.active_properties ?? 0) === 0 &&
    (summary?.active_contracts ?? 0) === 0;

  const needsContractHint =
    !showOnboardingNow &&
    (summary?.active_properties ?? 0) > 0 &&
    (summary?.active_contracts ?? 0) === 0;

  const invalidateAll = () => invalidateDashboard(queryClient);
  const greeting = useMemo(() => getGreeting(), []);

  const isOwner = role === 'owner';
  const isManager = role === 'manager';
  const isAccountant = role === 'accountant';
  const showFinance = isOwner || isAccountant || isManager;
  const showProfitability = isOwner;
  const managerFirst = isManager;

  if (summaryQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-72" />
        <div className="flex flex-wrap gap-2">
          <Skeleton className="h-9 w-36 rounded-lg" />
          <Skeleton className="h-9 w-36 rounded-lg" />
          <Skeleton className="h-9 w-36 rounded-lg" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          <Skeleton className="h-56 rounded-xl lg:col-span-3" />
          <Skeleton className="h-56 rounded-xl lg:col-span-2" />
        </div>
        <Skeleton className="h-48 rounded-xl" />
      </div>
    );
  }

  if (summaryQuery.isError || !summary) {
    return (
      <ListErrorState
        message="Не удалось загрузить дашборд"
        onRetry={invalidateAll}
        isRetrying={summaryQuery.isFetching}
      />
    );
  }

  const GreetingIcon = greeting.Icon;
  const hasPortfolio = summary.active_contracts > 0 || summary.active_properties > 0;
  const collected = Number(summary.monthly_collected_income);
  const expected = Number(summary.monthly_expected_income);
  const remaining = Math.max(0, expected - collected);

  const subtitle = (() => {
    if (!hasPortfolio) return 'Добавьте первый объект, чтобы начать';
    if (needsContractHint) return 'Есть объекты без активного договора — создайте договор';
    if (isManager) return 'Задачи и события по портфелю';
    if (isAccountant) return 'Платежи и начисления за период';
    return 'Сводка по портфелю';
  })();

  const primaryColumn = (
    <>
      <AttentionPanel
        overdueChargesCount={summary.overdue_count ?? 0}
        overdueChargesAmount={summary.overdue_total_amount || '0'}
        overdueContractsCount={overdueContractsCount}
        remainingToCollect={remaining}
        collected={collected}
        expected={expected}
      />
      {managerFirst ? <UpcomingEventsWidget /> : <AnalyticsWidget showProfitability={showProfitability} />}
    </>
  );

  const secondaryColumn = (
    <>
      {managerFirst ? (
        <AnalyticsWidget showProfitability={false} defaultTab="forecast" />
      ) : (
        <UpcomingEventsWidget />
      )}
    </>
  );

  return (
    <motion.div initial="hidden" animate="show" className="space-y-4">
      <motion.div variants={fadeUp} className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600 flex-shrink-0">
            <GreetingIcon className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="text-base font-medium text-gray-900 truncate">
              {greeting.text}
              {user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}
            </p>
            <p className="text-xs text-gray-500">{subtitle}</p>
          </div>
        </div>
        <RefreshButton onClick={invalidateAll} isLoading={summaryQuery.isFetching} />
      </motion.div>

      <motion.div variants={fadeUp}>
        <QuickActions />
      </motion.div>

      {showOnboardingNow && (
        <motion.div variants={fadeUp}>
          <OnboardingWizard onComplete={() => setShowOnboarding(false)} />
        </motion.div>
      )}

      {needsContractHint && (
        <motion.div variants={fadeUp}>
          <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <p className="text-sm text-blue-900">
              Объекты добавлены, но активных договоров нет — без договора не будет начислений и
              прогноза.
            </p>
            <Link
              to="/contracts"
              className="text-sm font-medium text-blue-800 hover:text-blue-950 flex-shrink-0"
            >
              Создать договор
            </Link>
          </div>
        </motion.div>
      )}

      <motion.div variants={fadeUp}>
        <DashboardKpiBar
          summary={summary}
          overdueContractsCount={overdueContractsCount}
          showFinance={showFinance}
        />
      </motion.div>

      <motion.div variants={fadeUp} className="grid grid-cols-1 lg:grid-cols-5 gap-4 items-start">
        <div className="lg:col-span-3 space-y-4">{primaryColumn}</div>
        <div className="lg:col-span-2 space-y-4">{secondaryColumn}</div>
      </motion.div>

      <motion.div variants={fadeUp}>
        <PropertiesOverview data={summary.properties_overview || []} />
      </motion.div>
    </motion.div>
  );
}
