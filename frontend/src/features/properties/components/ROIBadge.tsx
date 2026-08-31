import { TrendingUp, HelpCircle } from 'lucide-react';

interface ROIBadgeProps {
  roi: number | null | undefined;
  size?: 'sm' | 'md';
}

export function ROIBadge({ roi, size = 'md' }: ROIBadgeProps) {
  if (roi === null || roi === undefined) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-gray-400">
        <HelpCircle className={size === 'sm' ? 'h-3 w-3' : 'h-4 w-4'} />
        —
      </span>
    );
  }

  const color = roi >= 10 ? 'text-green-600 bg-green-50' : roi >= 5 ? 'text-amber-600 bg-amber-50' : 'text-gray-500 bg-gray-100';

  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>
      <TrendingUp className="h-3 w-3" />
      {roi.toFixed(1)}%
    </span>
  );
}
