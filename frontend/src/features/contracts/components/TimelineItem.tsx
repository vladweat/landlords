import { StickyNote, Bell, RefreshCw, CreditCard, FileX } from 'lucide-react';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import type { EventType } from '@/entities/contract';
import { cn } from '@/shared/lib/utils';

const meta: Record<EventType, { icon: typeof StickyNote; color: string; bg: string; label: string }> = {
  note: { icon: StickyNote, color: 'text-blue-600', bg: 'bg-blue-50', label: 'Заметка' },
  reminder: { icon: Bell, color: 'text-orange-600', bg: 'bg-orange-50', label: 'Напоминание' },
  status_change: { icon: RefreshCw, color: 'text-violet-600', bg: 'bg-violet-50', label: 'Статус' },
  payment: { icon: CreditCard, color: 'text-emerald-600', bg: 'bg-emerald-50', label: 'Платёж' },
  termination: { icon: FileX, color: 'text-amber-700', bg: 'bg-amber-50', label: 'Расторжение' },
  renewal: { icon: RefreshCw, color: 'text-sky-700', bg: 'bg-sky-50', label: 'Продление' },
};

interface TimelineItemProps {
  event_type: EventType;
  title: string;
  description: string;
  created_at: string;
  isLast?: boolean;
}

export function TimelineItem({
  event_type,
  title,
  description,
  created_at,
  isLast,
}: TimelineItemProps) {
  const cfg = meta[event_type] || meta.note;
  const Icon = cfg.icon;
  const timeLabel = format(new Date(created_at), 'd MMM, HH:mm', { locale: ru });

  return (
    <div className="relative flex gap-3 sm:gap-4">
      {!isLast && (
        <span
          className="absolute left-[17px] top-9 bottom-0 w-px bg-gray-100"
          aria-hidden
        />
      )}
      <div
        className={cn(
          'relative z-[1] flex h-9 w-9 shrink-0 items-center justify-center rounded-full ring-4 ring-white',
          cfg.bg,
        )}
      >
        <Icon className={cn('h-4 w-4', cfg.color)} />
      </div>
      <div className="min-w-0 flex-1 pb-5">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <div className="min-w-0">
            <span className="mr-2 text-[11px] font-medium uppercase tracking-wide text-gray-400">
              {cfg.label}
            </span>
            <p className="text-sm font-medium text-gray-900">{title}</p>
          </div>
          <time className="shrink-0 text-xs tabular-nums text-gray-400">{timeLabel}</time>
        </div>
        {description ? (
          <p className="mt-1 text-sm leading-relaxed text-gray-500 whitespace-pre-wrap">{description}</p>
        ) : null}
      </div>
    </div>
  );
}
