import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '@/features/auth/store';

export function ProtectedRoute() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const token = localStorage.getItem('access_token');

  if (!isAuthenticated && !token) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
