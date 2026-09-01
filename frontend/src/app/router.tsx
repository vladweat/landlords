import { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { FullPageLoader } from '@/shared/ui/FullPageLoader';
import { ProtectedRoute } from './ProtectedRoute';
import { useAuthStore } from '@/features/auth/store';

const LoginPage = lazy(() => import('@/pages/login/LoginPage'));
const ForgotPasswordPage = lazy(() => import('@/pages/forgot-password/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('@/pages/reset-password/ResetPasswordPage'));
const AppLayout = lazy(() => import('@/pages/layout/AppLayout'));
const DashboardPage = lazy(() => import('@/pages/dashboard/DashboardPage'));
const PropertiesPage = lazy(() => import('@/pages/properties/PropertiesPage'));
const TenantsPage = lazy(() => import('@/pages/tenants/TenantsPage'));
const ContractsPage = lazy(() => import('@/pages/contracts/ContractsPage'));
const ContractDetailPage = lazy(() => import('@/pages/contracts/ContractDetailPage'));
const PaymentsPage = lazy(() => import('@/pages/payments/PaymentsPage'));
const ExpensesPage = lazy(() => import('@/pages/expenses/ExpensesPage'));
const SettingsPage = lazy(() => import('@/pages/settings/SettingsPage'));
const NotFound = lazy(() => import('@/pages/NotFound'));

function HomeRedirect() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  window.location.href = '/landing.html';
  return null;
}

export function AppRouter() {
  return (
    <Suspense fallback={<FullPageLoader />}>
      <Routes>
        <Route path="/" element={<HomeRedirect />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/properties" element={<PropertiesPage />} />
            <Route path="/tenants" element={<TenantsPage />} />
            <Route path="/contracts" element={<ContractsPage />} />
            <Route path="/contracts/:id" element={<ContractDetailPage />} />
            <Route path="/payments" element={<PaymentsPage />} />
            <Route path="/expenses" element={<ExpensesPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
