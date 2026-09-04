import { useAuthStore } from '@/features/auth/store';
import { hasPermission, type Permission } from '@/entities/account';

/** Проверить право текущего пользователя. */
export function useCan(permission: Permission): boolean {
  const role = useAuthStore((s) => s.role);
  return hasPermission(role, permission);
}
