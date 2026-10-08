import { beforeEach, describe, expect, it, vi } from 'vitest';

const getMe = vi.fn();
const logout = vi.fn();

vi.mock('@/app/providers', () => ({
  queryClient: { clear: vi.fn() },
}));

vi.mock('./api', () => ({
  authApi: {
    getMe: (...args: unknown[]) => getMe(...args),
    logout: (...args: unknown[]) => logout(...args),
  },
}));

describe('auth store', () => {
  beforeEach(async () => {
    localStorage.clear();
    getMe.mockReset();
    logout.mockReset();
    logout.mockResolvedValue({ status: 'success' });
    const { useAuthStore } = await import('./store');
    useAuthStore.setState({
      user: null,
      account: null,
      role: null,
      isAuthenticated: false,
      isLoading: true,
    });
  });

  it('не кладёт JWT в localStorage', async () => {
    const { useAuthStore } = await import('./store');
    useAuthStore.getState().setAuth({
      id: 'u1',
      email: 'a@b.c',
      full_name: 'A',
      phone: null,
    });
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it('bootstrap поднимает сессию из cookie через /auth/me', async () => {
    getMe.mockResolvedValue({
      data: {
        user: { id: 'u1', email: 'a@b.c', full_name: 'A', phone: null, is_active: true },
        account: { id: 'acc', name: 'Acc' },
        role: 'owner',
      },
    });
    const { useAuthStore } = await import('./store');
    await useAuthStore.getState().bootstrap();
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().role).toBe('owner');
    expect(useAuthStore.getState().isLoading).toBe(false);
  });

  it('bootstrap без сессии оставляет гостя', async () => {
    getMe.mockRejectedValue(new Error('401'));
    const { useAuthStore } = await import('./store');
    await useAuthStore.getState().bootstrap();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().isLoading).toBe(false);
  });
});
