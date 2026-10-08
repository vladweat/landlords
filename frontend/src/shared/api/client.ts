import axios from 'axios';
import type { AxiosError } from 'axios';

const LEGACY_TOKEN_KEY = 'access_token';

export const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
  withCredentials: true,
});

apiClient.interceptors.request.use((config) => {
  // Старые сессии: один раз шлём Bearer, /auth/me переложит JWT в HttpOnly-cookie.
  const legacy = localStorage.getItem(LEGACY_TOKEN_KEY);
  if (legacy && config.headers) {
    config.headers.Authorization = `Bearer ${legacy}`;
  }
  // FormData: пусть браузер выставит multipart boundary
  if (typeof FormData !== 'undefined' && config.data instanceof FormData && config.headers) {
    delete config.headers['Content-Type'];
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const url = error.config?.url ?? '';
    const isAuthEntry = url.includes('/auth/login') || url.includes('/auth/logout') || url.includes('/auth/register');
    if (error.response?.status === 401 && !isAuthEntry) {
      // Динамический импорт, чтобы избежать циклической зависимости client ↔ store
      void import('@/features/auth/store').then(({ useAuthStore }) => {
        const { isAuthenticated } = useAuthStore.getState();
        if (isAuthenticated || localStorage.getItem(LEGACY_TOKEN_KEY)) {
          useAuthStore.getState().logout();
        }
      });
    }
    return Promise.reject(error);
  }
);

/** Скачивание файла той же сессией (cookie или временный Bearer). */
export async function authorizedFetch(url: string): Promise<Response> {
  const legacy = localStorage.getItem(LEGACY_TOKEN_KEY);
  return fetch(url, {
    credentials: 'include',
    headers: legacy ? { Authorization: `Bearer ${legacy}` } : {},
  });
}
