import { useEffect, useMemo, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { X, PanelLeft, LogOut, MessageSquare } from 'lucide-react';
import { useAuthStore } from '@/features/auth/store';
import { hasPermission } from '@/entities/account';
import { notificationsApi } from '@/features/notifications/api';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { FeedbackModal } from '@/features/feedback/components/FeedbackModal';
import {
  NAV_SECTIONS,
  ProfileIcon,
  findActiveNavLabel,
  isNavItemVisible,
  type NavBadgeKey,
  type NavItem,
} from './sidebarConfig';

interface SidebarProps {
  open: boolean;
  collapsed: boolean;
  onClose: () => void;
  onToggleCollapse: () => void;
}

function Badge({ count, collapsed }: { count: number; collapsed: boolean }) {
  if (count <= 0) return null;
  const label = count > 99 ? '99+' : String(count);
  return (
    <span
      className={`flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white ${
        collapsed ? 'absolute -right-1 -top-1' : 'ml-auto'
      }`}
    >
      {label}
    </span>
  );
}

export function Sidebar({ open, collapsed, onClose, onToggleCollapse }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, account, role, logout } = useAuthStore();
  const [showLogout, setShowLogout] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [settingsExpanded, setSettingsExpanded] = useState(
    () => location.pathname.startsWith('/settings'),
  );

  useEffect(() => {
    if (location.pathname.startsWith('/settings')) {
      setSettingsExpanded(true);
    } else {
      setSettingsExpanded(false);
    }
  }, [location.pathname]);

  const { data: notifications } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationsApi.list(),
    refetchInterval: 60_000,
  });

  const badges = useMemo(() => {
    const counts: Record<NavBadgeKey, number> = {
      overdue_payments: 0,
      ending_contracts: 0,
      billing_issue: 0,
    };
    for (const item of notifications?.items ?? []) {
      if (item.type === 'charge_overdue') counts.overdue_payments += 1;
      if (item.type === 'contract_ending') counts.ending_contracts += 1;
    }
    if (role === 'owner' && account?.subscription_status === 'past_due') {
      counts.billing_issue = 1;
    }
    return counts;
  }, [notifications?.items, account?.subscription_status, role]);

  const sections = useMemo(
    () =>
      NAV_SECTIONS.map((section) => ({
        ...section,
        items: section.items.filter((item) => isNavItemVisible(item, role)),
      })).filter((section) => section.items.length > 0),
    [role],
  );

  const currentLabel = findActiveNavLabel(location.pathname);
  const onSettings = location.pathname.startsWith('/settings');

  const renderItem = (item: NavItem) => {
    const isActive = location.pathname.startsWith(item.href);
    const badgeCount = item.badgeKey ? badges[item.badgeKey] : 0;
    const hasChildren = Boolean(item.children?.length);
    const showChildren =
      !collapsed && hasChildren && isActive && settingsExpanded;

    const visibleChildren = item.children?.filter((child) => {
      if (!child.requiredPermission) return true;
      return hasPermission(role, child.requiredPermission);
    });

    return (
      <div key={item.id}>
        <NavLink
          to={item.href}
          onClick={(e) => {
            if (hasChildren && onSettings && item.id === 'settings') {
              e.preventDefault();
              setSettingsExpanded((prev) => !prev);
              return;
            }
            onClose();
          }}
          title={collapsed ? item.label : undefined}
          aria-label={item.label}
          aria-expanded={hasChildren ? showChildren : undefined}
          aria-current={isActive ? 'page' : undefined}
          className={`relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
            isActive
              ? 'bg-blue-50 text-blue-700'
              : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
          } ${collapsed ? 'justify-center px-2' : ''} ${
            isActive && collapsed ? 'ring-2 ring-inset ring-blue-200' : ''
          }`}
        >
          {isActive && !collapsed && (
            <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r bg-blue-600" />
          )}
          <span className="relative flex-shrink-0">
            <item.icon className="h-5 w-5" />
            {collapsed && <Badge count={badgeCount} collapsed />}
          </span>
          {!collapsed && (
            <>
              <span className="truncate">{item.label}</span>
              <Badge count={badgeCount} collapsed={false} />
            </>
          )}
        </NavLink>

        {showChildren && visibleChildren && visibleChildren.length > 0 && (
          <div className="ml-4 mt-1 space-y-0.5 border-l border-gray-200 pl-3">
            {visibleChildren.map((child) => {
              const childActive =
                location.hash === `#${child.id}` ||
                (child.id === 'personal' && onSettings && !location.hash);
              return (
                <a
                  key={child.id}
                  href={child.href}
                  onClick={onClose}
                  className={`block rounded-md px-2 py-1.5 text-xs font-medium transition-colors ${
                    childActive
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-500 hover:bg-gray-100 hover:text-gray-800'
                  }`}
                >
                  {child.label}
                </a>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  const sidebarContent = (
    <div
      className={`flex h-full flex-col bg-white border-r border-gray-200 transition-all duration-200 ${
        collapsed ? 'w-14' : 'w-56'
      }`}
    >
      <div
        className={`flex h-16 items-center border-b border-gray-200 px-4 ${
          collapsed ? 'justify-center' : 'justify-between'
        }`}
      >
        {!collapsed && <h1 className="text-xl font-bold text-blue-600">Landlords</h1>}
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onToggleCollapse}
            className="hidden lg:flex rounded-lg p-1.5 text-gray-500 hover:bg-gray-100"
            title={collapsed ? 'Развернуть меню' : 'Свернуть меню'}
            aria-label={collapsed ? 'Развернуть меню' : 'Свернуть меню'}
          >
            <PanelLeft className={`h-5 w-5 transition-transform ${collapsed ? 'rotate-180' : ''}`} />
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 lg:hidden"
            aria-label="Закрыть меню"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      {!collapsed && currentLabel && (
        <div className="border-b border-gray-100 px-4 py-2 lg:hidden">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Сейчас</p>
          <p className="text-sm font-medium text-gray-800">{currentLabel}</p>
        </div>
      )}

      <nav
        className="flex-1 space-y-4 overflow-y-auto p-3 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden"
        aria-label="Основная навигация"
      >
        {sections.map((section) => (
          <div key={section.id}>
            {!collapsed && (
              <p className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                {section.label}
              </p>
            )}
            {collapsed && section.id !== sections[0]?.id && (
              <div className="mx-auto mb-1.5 h-px w-6 bg-gray-200" aria-hidden />
            )}
            <div className="space-y-1">{section.items.map(renderItem)}</div>
          </div>
        ))}
      </nav>

      <div className="border-t border-gray-200 p-3 space-y-1">
        <button
          type="button"
          onClick={() => {
            setShowFeedback(true);
            onClose();
          }}
          title="Обратная связь"
          aria-label="Обратная связь"
          className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-800 transition-colors ${
            collapsed ? 'justify-center px-2' : ''
          }`}
        >
          <MessageSquare className="h-4 w-4 flex-shrink-0" />
          {!collapsed && 'Обратная связь'}
        </button>

        {collapsed ? (
          <button
            type="button"
            onClick={() => setShowLogout(true)}
            className="flex w-full justify-center rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
            title={user?.full_name ? `${user.full_name} — выйти` : 'Выйти'}
            aria-label="Выйти"
          >
            <LogOut className="h-4 w-4" />
          </button>
        ) : (
          <div className="flex items-center justify-between gap-1 rounded-lg px-1 py-1">
            <div className="flex min-w-0 items-center gap-2">
              <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-blue-100">
                <ProfileIcon className="h-3.5 w-3.5 text-blue-600" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-gray-700">
                  {user?.full_name || 'Пользователь'}
                </p>
                {role && (
                  <p className="truncate text-[11px] text-gray-400">
                    {role === 'owner' ? 'Владелец' : role === 'manager' ? 'Менеджер' : 'Бухгалтер'}
                  </p>
                )}
              </div>
            </div>
            <button
              type="button"
              onClick={() => setShowLogout(true)}
              className="flex-shrink-0 rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              title="Выйти"
              aria-label="Выйти"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <>
      <div className="hidden lg:flex lg:flex-shrink-0">{sidebarContent}</div>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-y-0 left-0 z-50 w-56 lg:hidden"
          >
            {sidebarContent}
          </motion.div>
        )}
      </AnimatePresence>
      <ConfirmDialog
        isOpen={showLogout}
        onClose={() => setShowLogout(false)}
        onConfirm={() => {
          logout();
          navigate('/login');
        }}
        title="Выйти из аккаунта?"
        message="Вы уверены, что хотите выйти?"
      />
      <FeedbackModal isOpen={showFeedback} onClose={() => setShowFeedback(false)} />
    </>
  );
}
