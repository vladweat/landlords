import { useState } from 'react';
import { BarChart3, ChevronDown } from 'lucide-react';
import { ForecastTab } from './ForecastTab';
import { ProfitabilityTab } from './ProfitabilityTab';
import { PaymentsChartTab } from './PaymentsChartTab';
import { DashboardSection } from './DashboardSection';
import { cn } from '@/shared/lib/utils';

type Tab = 'payments' | 'forecast' | 'profitability';

interface AnalyticsWidgetProps {
  showProfitability?: boolean;
  defaultTab?: Tab;
  /** В режиме командного центра аналитика свёрнута по умолчанию. */
  collapsible?: boolean;
  defaultOpen?: boolean;
}

export function AnalyticsWidget({
  showProfitability = true,
  defaultTab = 'payments',
  collapsible = false,
  defaultOpen = true,
}: AnalyticsWidgetProps) {
  const [tab, setTab] = useState<Tab>(defaultTab);
  const [open, setOpen] = useState(defaultOpen);

  const tabs: { id: Tab; label: string }[] = [
    { id: 'payments', label: 'Поступления' },
    { id: 'forecast', label: 'Прогноз' },
    ...(showProfitability ? [{ id: 'profitability' as const, label: 'Доходность' }] : []),
  ];

  const activeTab = tabs.some((t) => t.id === tab) ? tab : 'payments';

  if (collapsible) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="w-full flex items-center justify-between gap-2 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
        >
          <span className="text-sm font-medium text-gray-700 flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-blue-600" />
            Аналитика
          </span>
          <ChevronDown
            className={cn(
              'h-4 w-4 text-gray-400 transition-transform',
              open && 'rotate-180',
            )}
          />
        </button>
        {open && (
          <>
            <div className="flex flex-wrap border-t border-b border-gray-100" role="tablist">
              {tabs.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  role="tab"
                  aria-selected={activeTab === t.id}
                  onClick={() => setTab(t.id)}
                  className={cn(
                    'px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px',
                    activeTab === t.id
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700',
                  )}
                >
                  {t.label}
                </button>
              ))}
            </div>
            <div className="p-4">
              {activeTab === 'payments' && <PaymentsChartTab />}
              {activeTab === 'forecast' && <ForecastTab />}
              {activeTab === 'profitability' && showProfitability && <ProfitabilityTab />}
            </div>
          </>
        )}
      </div>
    );
  }

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
