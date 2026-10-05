import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { Card } from '@/shared/ui/Card';
import { cn } from '@/shared/lib/utils';

interface DashboardSectionProps {
  title: string;
  icon?: ReactNode;
  action?: { label: string; to: string };
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  flush?: boolean;
}

/** Единый каркас секции дашборда: заголовок, вторичный action, контент. */
export function DashboardSection({
  title,
  icon,
  action,
  children,
  className,
  bodyClassName,
  flush = false,
}: DashboardSectionProps) {
  return (
    <Card className={cn('p-0 overflow-hidden shadow-sm', className)}>
      <div className="flex items-center justify-between gap-2 px-4 py-3 border-b border-gray-100">
        <h2 className="text-sm font-medium text-gray-700 flex items-center gap-2 min-w-0">
          {icon}
          <span className="truncate">{title}</span>
        </h2>
        {action && (
          <Link
            to={action.to}
            className="flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-800 flex-shrink-0"
          >
            {action.label}
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        )}
      </div>
      <div className={cn(flush ? '' : 'p-4', bodyClassName)}>{children}</div>
    </Card>
  );
}
