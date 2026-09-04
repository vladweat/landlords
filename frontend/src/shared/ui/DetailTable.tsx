import type { HTMLAttributes, ReactNode, TdHTMLAttributes, ThHTMLAttributes } from 'react';
import { cn } from '@/shared/lib/utils';

interface DetailTableProps {
  children: ReactNode;
  className?: string;
  footnote?: ReactNode;
}

/** Единый каркас таблиц в детальных карточках: рамка, шапка, отступы. */
export function DetailTable({ children, className, footnote }: DetailTableProps) {
  return (
    <div className={cn('space-y-3', className)}>
      {footnote ? <p className="text-xs text-gray-500 leading-relaxed">{footnote}</p> : null}
      <div className="rounded-xl border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto overflow-y-clip [scrollbar-width:thin]">
          <table className="w-full text-sm">{children}</table>
        </div>
      </div>
    </div>
  );
}

export function DetailTh({
  align = 'left',
  className,
  children,
  ...props
}: ThHTMLAttributes<HTMLTableCellElement> & { align?: 'left' | 'right' }) {
  return (
    <th
      className={cn(
        'bg-gray-50 py-2.5 px-3 text-xs font-medium uppercase tracking-wide text-gray-500 whitespace-nowrap first:pl-4 last:pr-4',
        align === 'right' ? 'text-right' : 'text-left',
        className,
      )}
      {...props}
    >
      {children}
    </th>
  );
}

export function DetailTd({
  align = 'left',
  muted,
  mono,
  wrap,
  className,
  children,
  ...props
}: TdHTMLAttributes<HTMLTableCellElement> & {
  align?: 'left' | 'right';
  muted?: boolean;
  mono?: boolean;
  wrap?: boolean;
}) {
  return (
    <td
      className={cn(
        'py-3 px-3 first:pl-4 last:pr-4',
        !wrap && 'whitespace-nowrap',
        align === 'right' && 'text-right',
        mono && 'tabular-nums',
        muted ? 'text-gray-500' : 'text-gray-800',
        className,
      )}
      {...props}
    >
      {children}
    </td>
  );
}

export function DetailTr({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn(
        'border-b border-gray-100 last:border-0 transition-colors hover:bg-gray-50/80',
        className,
      )}
      {...props}
    >
      {children}
    </tr>
  );
}

export function StatusDot({
  colorClass,
  label,
  muted,
}: {
  colorClass: string;
  label: string;
  muted?: boolean;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-2 text-sm',
        muted ? 'text-gray-500' : 'text-gray-700',
      )}
    >
      <span className={cn('h-2 w-2 shrink-0 rounded-full', colorClass)} />
      {label}
    </span>
  );
}
