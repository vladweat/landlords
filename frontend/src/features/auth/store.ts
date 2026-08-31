import { create } from 'zustand';
import type { User } from '@/entities/user';
import { authApi } from './api';
import { queryClient } from '@/app/providers';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setAuth: (user: User, token: string) => void;
  logout: () => void;
  loadFromStorage: () => void;
  fetchUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,

  setAuth: (user: User, token: string) => {
    localStorage.setItem('access_token', token);
    set({ user, token, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem('access_token');
    queryClient.clear();
    set({ user: null, token: null, isAuthenticated: false });
  },

  loadFromStorage: () => {
    const token = localStorage.getItem('access_token');
    if (token) {
      set({ token, isAuthenticated: true });
      get().fetchUser();
    }
  },

  fetchUser: async () => {
    set({ isLoading: true });
    try {
      const response = await authApi.getMe();
      set({ user: response.user, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },
}));
