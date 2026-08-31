import { apiClient } from '@/shared/api/client';
import type { LoginFormData } from './schema';

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface AuthResponse {
  status: string;
  token: string;
  user: {
    id: string;
    email: string;
    full_name: string;
  };
}

export interface MeResponse {
  status: string;
  user: {
    id: string;
    email: string;
    full_name: string;
    is_active: boolean;
  };
}

export const authApi = {
  login: async (data: LoginFormData): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/auth/login', {
      email: data.email,
      password: data.password,
    });
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/auth/register', data);
    return response.data;
  },

  getMe: async () => {
    const response = await apiClient.get<MeResponse>('/auth/me');
    return response.data;
  },

  updateProfile: async (data: { full_name?: string; phone?: string }) => {
    const response = await apiClient.put<{ status: string; data: { id: string; email: string; full_name: string; is_active: boolean } }>('/auth/me', data);
    return response.data;
  },

  changePassword: async (data: { current_password: string; new_password: string }) => {
    const response = await apiClient.post<{ message: string }>('/auth/change-password', data);
    return response.data;
  },

  forgotPassword: async (email: string) => {
    const response = await apiClient.post<{ message: string }>('/auth/forgot-password', { email });
    return response.data;
  },

  resetPassword: async (data: { token: string; new_password: string }) => {
    const response = await apiClient.post<{ message: string }>('/auth/reset-password', data);
    return response.data;
  },

  deleteAccount: async () => {
    const response = await apiClient.delete<{ message: string }>('/auth/me', { data: { confirmation: 'DELETE' } });
    return response.data;
  },
};
