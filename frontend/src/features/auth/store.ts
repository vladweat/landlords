import { create } from 'zustand';
import type { User } from '@/entities/user';
import type { Account, Role } from '@/entities/account';
import { authApi } from './api';
import { queryClient } from '@/app/providers';

const LEGACY_TOKEN_KEY = 'access_token';

interface AuthState {
  user: User | null;
  account: Account | null;
  role: Role | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setAuth: (user: User) => void;
  logout: () => void;
  bootstrap: () => Promise<void>;
  fetchUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  account: null,
  role: null,
  isAuthenticated: false,
  isLoading: true,

  setAuth: (user: User) => {
    localStorage.removeItem(LEGACY_TOKEN_KEY);
    set({ user, isAuthenticated: true, isLoading: false });
  },

  logout: () => {
    localStorage.removeItem(LEGACY_TOKEN_KEY);
    queryClient.clear();
    set({
      user: null,
      account: null,
      role: null,
      isAuthenticated: false,
      isLoading: false,
    });
    void authApi.logout().catch(() => undefined);
  },

  bootstrap: async () => {
    set({ isLoading: true });
    try {
      const response = await authApi.getMe();
      localStorage.removeItem(LEGACY_TOKEN_KEY);
      set({
        user: response.data.user,
        account: response.data.account,
        role: response.data.role,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      localStorage.removeItem(LEGACY_TOKEN_KEY);
      set({
        user: null,
        account: null,
        role: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },

  fetchUser: async () => {
    set({ isLoading: true });
    try {
      const response = await authApi.getMe();
      set({
        user: response.data.user,
        account: response.data.account,
        role: response.data.role,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      get().logout();
    }
  },
}));
