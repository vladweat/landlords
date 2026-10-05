import type { ReactNode } from 'react';
import { cn } from '@/shared/lib/utils';

interface MobileListProps {
  children: ReactNode;
  className?: string;
}

/** Контейнер мобильного списка (виден только < sm). */
export function MobileList({ children, className }: MobileListProps) {
  return <div className={cn('sm:hidden space-y-2', className)}>{children}</div>;
}

interface MobileListItemProps {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
  /** Правая зона: меню действий, чекбокс и т.п. */
  trailing?: ReactNode;
  /** Левая зона перед контентом (чекбокс). */
  leading?: ReactNode;
}

export function MobileListItem({
  children,
  onClick,
  className,
  trailing,
  leading,
}: MobileListItemProps) {
  const Comp = onClick ? 'button' : 'div';
  return (
    <div
      className={cn(
        'flex items-center gap-3 rounded-xl border border-gray-100 bg-white px-3 py-3',
        className,
      )}
    >
      {leading}
      <Comp
        type={onClick ? 'button' : undefined}
        onClick={onClick}
        className={cn(
          'min-w-0 flex-1 text-left',
          onClick && 'hover:text-blue-600 transition-colors',
        )}
      >
        {children}
      </Comp>
      {trailing ? <div className="flex-shrink-0">{trailing}</div> : null}
    </div>
  );
}
