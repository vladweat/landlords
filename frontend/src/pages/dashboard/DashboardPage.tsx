import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Sun, Moon, Sunset } from 'lucide-react';
import { dashboardApi } from '@/features/dashboard/api';
import { AnalyticsWidget } from '@/features/dashboard/components/AnalyticsWidget';
import { PropertiesOverview } from '@/features/dashboard/components/PropertiesOverview';
import { AttentionFeed } from '@/features/dashboard/components/AttentionFeed';
import { CommandHeader } from '@/features/dashboard/components/CommandHeader';
import { OnboardingWizard } from '@/features/onboarding/OnboardingWizard';
import { Skeleton } from '@/shared/ui/Skeleton';
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
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
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

  if (summaryQuery.isLoading) {
    return (
      <div className="space-y-4 max-w-5xl mx-auto">
        <Skeleton className="h-44 rounded-2xl" />
        <Skeleton className="h-64 rounded-xl" />
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

  const hasPortfolio = summary.active_contracts > 0 || summary.active_properties > 0;

  const subtitle = (() => {
    if (!hasPortfolio) return 'Добавьте первый объект, чтобы начать';
    if (needsContractHint) return 'Есть объекты без активного договора — создайте договор';
    if (isManager) return 'Задачи и события по портфелю';
    if (isAccountant) return 'Платежи и начисления за период';
    return 'Сводка по портфелю';
  })();

  const greetingText = `${greeting.text}${user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}`;

  return (
    <motion.div initial="hidden" animate="show" className="space-y-4 max-w-5xl mx-auto">
      <motion.div variants={fadeUp}>
        <CommandHeader
          greetingText={greetingText}
          greetingIcon={greeting.Icon}
          subtitle={subtitle}
          summary={summary}
          overdueContractsCount={overdueContractsCount}
          showFinance={showFinance}
          onRefresh={invalidateAll}
          isRefreshing={summaryQuery.isFetching}
        />
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
        <AttentionFeed
          overdueChargesCount={summary.overdue_count ?? 0}
          overdueChargesAmount={summary.overdue_total_amount || '0'}
          overdueContractsCount={overdueContractsCount}
        />
      </motion.div>

      <motion.div variants={fadeUp}>
        <PropertiesOverview data={summary.properties_overview || []} />
      </motion.div>

      <motion.div variants={fadeUp}>
        <AnalyticsWidget
          showProfitability={showProfitability}
          collapsible
          defaultOpen={false}
        />
      </motion.div>
    </motion.div>
  );
}
