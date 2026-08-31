import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { dashboardApi } from '@/features/dashboard/api';
import { Skeleton } from '@/shared/ui/Skeleton';
import { shortAddress } from '@/shared/lib/address';

function roiColor(roi: number): string {
  if (roi >= 10) return '#059669';
  if (roi >= 5) return '#d97706';
  return '#9ca3af';
}

export function ProfitabilityTab() {
  const [showAll, setShowAll] = useState(false);
  const { data: summary, isLoading } = useQuery({ queryKey: ['dashboard-summary'], queryFn: dashboardApi.getSummary });

  if (isLoading) return <div className="space-y-3"><Skeleton className="h-5 w-32" /><Skeleton className="h-8 w-24" /></div>;
  if (!summary) return <p className="text-sm text-gray-500">Нет данных</p>;

  const portfolioRoi = summary.portfolio_roi?.portfolio_roi;
  const count = summary.portfolio_roi?.properties_with_roi;

  if (portfolioRoi === null || portfolioRoi === undefined || count === 0) {
    return <div className="text-center py-6"><p className="text-sm text-gray-500">Укажите стоимость объектов для расчёта доходности</p></div>;
  }

  const items = (summary.properties_overview || [])
    .filter(p => p.roi !== null)
    .sort((a, b) => (b.roi || 0) - (a.roi || 0));

  const maxRoi = items[0]?.roi || 1;
  const visible = showAll ? items : items.slice(0, 5);

  return (
    <div>
      <div className="flex items-baseline gap-2 mb-4">
        <span className="text-2xl font-semibold text-gray-900">{portfolioRoi.toFixed(1)}%</span>
        <span className="text-sm text-gray-500">по {count} объектам</span>
      </div>
      <div className="space-y-2">
        {visible.map((p) => {
          const roi = p.roi || 0;
          const width = (roi / maxRoi) * 100;
          return (
            <div key={p.property_id} className="flex items-center gap-2 text-sm">
              <span className="text-gray-600 w-36 flex-shrink-0 truncate">{shortAddress(p.address)}</span>
              <div className="flex-1 h-4 bg-gray-50 rounded">
                <div className="h-full rounded transition-all" style={{ width: `${Math.max(width, 4)}%`, background: roiColor(roi) }} />
              </div>
              <span className="text-gray-900 font-medium w-12 text-right flex-shrink-0">{roi.toFixed(1)}%</span>
            </div>
          );
        })}
      </div>
      {items.length > 5 && (
        <button onClick={() => setShowAll(!showAll)} className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 mt-3">
          {showAll ? <><ChevronUp className="h-3 w-3" /> Свернуть</> : <><ChevronDown className="h-3 w-3" /> Показать все ({items.length})</>}
        </button>
      )}
    </div>
  );
}
