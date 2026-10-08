import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '@/features/auth/store';
import { FullPageLoader } from '@/shared/ui/FullPageLoader';

export function ProtectedRoute() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isLoading = useAuthStore((state) => state.isLoading);

  if (isLoading) return <FullPageLoader />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return <Outlet />;
}
