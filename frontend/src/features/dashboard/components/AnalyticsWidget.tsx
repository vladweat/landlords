import { useState } from 'react';
import { ForecastTab } from './ForecastTab';
import { ProfitabilityTab } from './ProfitabilityTab';
import { PaymentsChartTab } from './PaymentsChartTab';
import { DashboardSection } from './DashboardSection';
import { BarChart3 } from 'lucide-react';
import { cn } from '@/shared/lib/utils';

type Tab = 'payments' | 'forecast' | 'profitability';

interface AnalyticsWidgetProps {
  /** Показывать вкладку доходности (обычно owner). */
  showProfitability?: boolean;
  /** Стартовая вкладка — для manager лучше события/прогноз не приоритетны. */
  defaultTab?: Tab;
}

export function AnalyticsWidget({
  showProfitability = true,
  defaultTab = 'payments',
}: AnalyticsWidgetProps) {
  const [tab, setTab] = useState<Tab>(defaultTab);

  const tabs: { id: Tab; label: string }[] = [
    { id: 'payments', label: 'Поступления' },
    { id: 'forecast', label: 'Прогноз' },
    ...(showProfitability ? [{ id: 'profitability' as const, label: 'Доходность' }] : []),
  ];

  const activeTab = tabs.some((t) => t.id === tab) ? tab : 'payments';

  return (
    <DashboardSection
      title="Аналитика"
      icon={<BarChart3 className="h-4 w-4 text-blue-600" />}
      flush
      bodyClassName="p-0"
    >
      <div className="flex flex-wrap border-b border-gray-100" role="tablist">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={activeTab === t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              'px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px',
              activeTab === t.id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700',
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="p-4 sm:p-5">
        {activeTab === 'payments' && <PaymentsChartTab />}
        {activeTab === 'forecast' && <ForecastTab />}
        {activeTab === 'profitability' && showProfitability && <ProfitabilityTab />}
      </div>
    </DashboardSection>
  );
}
