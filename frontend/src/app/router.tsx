import { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { FullPageLoader } from '@/shared/ui/FullPageLoader';
import { ProtectedRoute } from './ProtectedRoute';
import { useAuthStore } from '@/features/auth/store';

const LoginPage = lazy(() => import('@/pages/login/LoginPage'));
const ForgotPasswordPage = lazy(() => import('@/pages/forgot-password/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('@/pages/reset-password/ResetPasswordPage'));
const InvitePage = lazy(() => import('@/pages/invite/InvitePage'));
const AppLayout = lazy(() => import('@/pages/layout/AppLayout'));
const DashboardPage = lazy(() => import('@/pages/dashboard/DashboardPage'));
const PropertiesPage = lazy(() => import('@/pages/properties/PropertiesPage'));
const PropertyDetailPage = lazy(() => import('@/pages/properties/PropertyDetailPage'));
const TenantsPage = lazy(() => import('@/pages/tenants/TenantsPage'));
const ContractsPage = lazy(() => import('@/pages/contracts/ContractsPage'));
const ContractDetailPage = lazy(() => import('@/pages/contracts/ContractDetailPage'));
const PaymentsPage = lazy(() => import('@/pages/payments/PaymentsPage'));
const CalendarPage = lazy(() => import('@/pages/calendar/CalendarPage'));
const ExpensesPage = lazy(() => import('@/pages/expenses/ExpensesPage'));
const ReportsPage = lazy(() => import('@/pages/reports/ReportsPage'));
const SettingsPage = lazy(() => import('@/pages/settings/SettingsPage'));
const InvoicePublicPage = lazy(() => import('@/pages/invoices/InvoicePublicPage'));
const TenantPortalPage = lazy(() => import('@/pages/portal/TenantPortalPage'));
const NotFound = lazy(() => import('@/pages/NotFound'));

function HomeRedirect() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  window.location.href = '/landing.html';
  return null;
}

/** Редирект авторизованных с публичных auth-страниц на дашборд. */
function GuestOnly({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const token = localStorage.getItem('access_token');
  if (isAuthenticated || token) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export function AppRouter() {
  return (
    <Suspense fallback={<FullPageLoader />}>
      <Routes>
        <Route path="/" element={<HomeRedirect />} />
        <Route path="/login" element={<GuestOnly><LoginPage /></GuestOnly>} />
        <Route path="/forgot-password" element={<GuestOnly><ForgotPasswordPage /></GuestOnly>} />
        <Route path="/reset-password" element={<GuestOnly><ResetPasswordPage /></GuestOnly>} />
        <Route path="/invite" element={<GuestOnly><InvitePage /></GuestOnly>} />
        <Route path="/i/:token" element={<InvoicePublicPage />} />
        <Route path="/t/:token" element={<TenantPortalPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/properties" element={<PropertiesPage />} />
            <Route path="/properties/:id" element={<PropertyDetailPage />} />
            <Route path="/tenants" element={<TenantsPage />} />
            <Route path="/contracts" element={<ContractsPage />} />
            <Route path="/contracts/:id" element={<ContractDetailPage />} />
            <Route path="/payments" element={<PaymentsPage />} />
            <Route path="/calendar" element={<CalendarPage />} />
            <Route path="/expenses" element={<ExpensesPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
