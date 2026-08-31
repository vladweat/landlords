import { useState } from 'react';
import { Card } from '@/shared/ui/Card';
import { ForecastTab } from './ForecastTab';
import { ProfitabilityTab } from './ProfitabilityTab';
import { PaymentsChartTab } from './PaymentsChartTab';

type Tab = 'forecast' | 'profitability' | 'payments';

export function AnalyticsWidget() {
  const [tab, setTab] = useState<Tab>('forecast');

  const tabs: { id: Tab; label: string }[] = [
    { id: 'forecast', label: 'Прогноз' },
    { id: 'profitability', label: 'Доходность' },
    { id: 'payments', label: 'Платежи' },
  ];

  return (
    <Card className="rounded-xl border border-gray-200 shadow-sm">
      <div className="flex border-b border-gray-100">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === t.id ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="p-5">
        {tab === 'forecast' && <ForecastTab />}
        {tab === 'profitability' && <ProfitabilityTab />}
        {tab === 'payments' && <PaymentsChartTab />}
      </div>
    </Card>
  );
}
