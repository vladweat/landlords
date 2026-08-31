import { useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { LayoutDashboard, Building2, Users, FileText, CreditCard, Settings, X, PanelLeft, LogOut, User, MessageSquare } from 'lucide-react';
import { useAuthStore } from '@/features/auth/store';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { FeedbackModal } from '@/features/feedback/components/FeedbackModal';

const navigation = [
  { name: 'Дашборд', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Объекты', href: '/properties', icon: Building2 },
  { name: 'Арендаторы', href: '/tenants', icon: Users },
  { name: 'Договоры', href: '/contracts', icon: FileText },
  { name: 'Платежи', href: '/payments', icon: CreditCard },
  { name: 'Настройки', href: '/settings', icon: Settings },
];

interface SidebarProps {
  open: boolean;
  collapsed: boolean;
  onClose: () => void;
  onToggleCollapse: () => void;
}

export function Sidebar({ open, collapsed, onClose, onToggleCollapse }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [showLogout, setShowLogout] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);

  const sidebarContent = (
    <div className={`flex h-full flex-col bg-white border-r border-gray-200 transition-all duration-200 ${collapsed ? 'w-14' : 'w-56'}`}>
      <div className={`flex h-16 items-center border-b border-gray-200 px-4 ${collapsed ? 'justify-center' : 'justify-between'}`}>
        {!collapsed && <h1 className="text-xl font-bold text-blue-600">Landlords</h1>}
        <div className="flex items-center gap-1">
          <button onClick={onToggleCollapse} className="hidden lg:flex rounded-lg p-1.5 text-gray-500 hover:bg-gray-100">
            <PanelLeft className={`h-5 w-5 transition-transform ${collapsed ? 'rotate-180' : ''}`} />
          </button>
          <button onClick={onClose} className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 lg:hidden">
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {navigation.map((item) => {
          const isActive = location.pathname.startsWith(item.href);
          return (
            <NavLink key={item.name} to={item.href} onClick={onClose}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${isActive ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'} ${collapsed ? 'justify-center' : ''}`}>
              <item.icon className="h-5 w-5 flex-shrink-0" />
              {!collapsed && item.name}
            </NavLink>
          );
        })}
        <button onClick={() => { setShowFeedback(true); onClose(); }}
          className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors w-full ${collapsed ? 'justify-center' : ''}`}>
          <MessageSquare className="h-5 w-5 flex-shrink-0" />
          {!collapsed && 'Обратная связь'}
        </button>
      </nav>
      <div className="border-t border-gray-200 p-3">
        {collapsed ? (
          <button onClick={() => setShowLogout(true)} className="flex justify-center rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors w-full" title="Выйти">
            <LogOut className="h-4 w-4" />
          </button>
        ) : (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 flex-shrink-0">
                <User className="h-3.5 w-3.5 text-blue-600" />
              </div>
              <span className="text-sm font-medium text-gray-700 truncate">{user?.full_name || 'Пользователь'}</span>
            </div>
            <button onClick={() => setShowLogout(true)} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 flex-shrink-0" title="Выйти">
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
          <motion.div initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }} transition={{ duration: 0.2 }} className="fixed inset-y-0 left-0 z-50 w-56 lg:hidden">
            {sidebarContent}
          </motion.div>
        )}
      </AnimatePresence>
      <ConfirmDialog
        isOpen={showLogout}
        onClose={() => setShowLogout(false)}
        onConfirm={() => { logout(); navigate('/login'); }}
        title="Выйти из аккаунта?"
        message="Вы уверены, что хотите выйти?"
      />
      <FeedbackModal isOpen={showFeedback} onClose={() => setShowFeedback(false)} />
    </>
  );
}
