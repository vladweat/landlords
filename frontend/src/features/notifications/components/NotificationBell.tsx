import { useEffect, useRef, useState, type MouseEvent } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Bell, X } from 'lucide-react';
import { notificationsApi } from '../api';
import type { NotificationItem } from '@/entities/notification';

function severityDot(severity: NotificationItem['severity']): string {
  return severity === 'critical' ? 'bg-red-500' : 'bg-amber-500';
}

function scrollMainToTop() {
  const main = document.querySelector('main');
  if (main instanceof HTMLElement) {
    main.scrollTo({ top: 0, behavior: 'smooth' });
  } else {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationsApi.list(),
    refetchInterval: 60_000,
  });

  const dismissMutation = useMutation({
    mutationFn: (key: string) => notificationsApi.dismiss(key),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, [open]);

  const items = data?.items ?? [];
  const unread = data?.unread_count ?? 0;

  const handleItemClick = (item: NotificationItem, e: MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    e.stopPropagation();
    const href = item.href?.trim() || '/dashboard';
    setOpen(false);
    if (location.pathname === href) {
      scrollMainToTop();
      return;
    }
    navigate(href);
  };

  return (
    <div className="relative ml-auto" ref={panelRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative rounded-lg p-2 text-gray-500 hover:bg-gray-100"
        aria-label="Уведомления"
        aria-expanded={open}
      >
        <Bell className="h-5 w-5" />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div
          className="absolute right-0 z-50 mt-2 w-80 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg sm:w-96"
          onPointerDown={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <h2 className="text-sm font-semibold text-gray-900">Требует внимания</h2>
            <span className="text-xs text-gray-500">{unread}</span>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {items.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-gray-500">
                Нет непрочитанных уведомлений
              </p>
            ) : (
              <ul className="divide-y divide-gray-100">
                {items.map((item) => (
                  <li key={item.id} className="group flex gap-2 px-3 py-3 hover:bg-gray-50">
                    <Link
                      to={item.href || '/dashboard'}
                      onClick={(e) => handleItemClick(item, e)}
                      className="flex min-w-0 flex-1 cursor-pointer gap-3 text-left"
                    >
                      <span
                        className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${severityDot(item.severity)}`}
                      />
                      <span className="min-w-0">
                        <span className="block text-sm font-medium text-gray-900">
                          {item.title}
                        </span>
                        <span className="mt-0.5 block truncate text-xs text-gray-500">
                          {item.body}
                        </span>
                      </span>
                    </Link>
                    <button
                      type="button"
                      title="Скрыть"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        dismissMutation.mutate(item.id);
                      }}
                      className="rounded p-1 text-gray-400 opacity-0 hover:bg-gray-200 hover:text-gray-600 group-hover:opacity-100"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
