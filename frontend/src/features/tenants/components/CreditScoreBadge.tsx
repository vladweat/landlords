import type { CreditScore } from '@/features/tenants/types';

interface CreditScoreBadgeProps {
  score?: CreditScore;
  size?: 'sm' | 'md';
}

const config: Record<CreditScore, { color: string; bg: string; label: string }> = {
  reliable:     { color: 'text-green-700', bg: 'bg-green-50', label: 'Надёжный' },
  average:      { color: 'text-amber-700', bg: 'bg-amber-50', label: 'Средний' },
  problematic:  { color: 'text-red-700', bg: 'bg-red-50', label: 'Проблемный' },
  no_data:      { color: 'text-gray-500', bg: 'bg-gray-100', label: 'Нет данных' },
};

const dots: Record<CreditScore, string> = {
  reliable: '🟢',
  average: '🟡',
  problematic: '🔴',
  no_data: '⚪',
};

export function CreditScoreBadge({ score = 'no_data', size = 'md' }: CreditScoreBadgeProps) {
  const c = config[score];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${c.bg} ${c.color}`}>
      <span className="text-xs">{dots[score]}</span>
      {c.label}
    </span>
  );
}
