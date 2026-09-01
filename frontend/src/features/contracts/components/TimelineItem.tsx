import { StickyNote, Bell, RefreshCw, CreditCard, FileX } from 'lucide-react';
import type { EventType } from '@/entities/contract';

const iconMap: Record<EventType, { icon: typeof StickyNote; color: string; bg: string }> = {
  note:    { icon: StickyNote, color: 'text-blue-600', bg: 'bg-blue-50' },
  reminder: { icon: Bell,       color: 'text-orange-600', bg: 'bg-orange-50' },
  status_change: { icon: RefreshCw, color: 'text-purple-600', bg: 'bg-purple-50' },
  payment: { icon: CreditCard,  color: 'text-green-600', bg: 'bg-green-50' },
  termination: { icon: FileX, color: 'text-amber-700', bg: 'bg-amber-50' },
  renewal: { icon: RefreshCw, color: 'text-blue-700', bg: 'bg-blue-50' },
};

interface TimelineItemProps {
  event_type: EventType;
  title: string;
  description: string;
  created_at: string;
}

export function TimelineItem({ event_type, title, description, created_at }: TimelineItemProps) {
  const { icon: Icon, color, bg } = iconMap[event_type] || iconMap.note;
  const isAuto = event_type !== 'note';

  return (
    <div className={`flex gap-4 py-3 ${isAuto ? 'opacity-75' : ''}`}>
      <div className={`flex h-9 w-9 items-center justify-center rounded-full flex-shrink-0 ${bg}`}>
        <Icon className={`h-4 w-4 ${color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900">{title}</p>
        <p className="text-sm text-gray-500 mt-0.5">{description}</p>
      </div>
      <time className="text-xs text-gray-400 whitespace-nowrap self-start mt-1">
        {new Date(created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
      </time>
    </div>
  );
}
