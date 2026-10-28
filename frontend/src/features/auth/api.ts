import { apiClient } from '@/shared/api/client';
import type { LoginFormData } from './schema';
import type { Account, Role } from '@/entities/account';
import type { User } from '@/entities/user';

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface AuthResponse {
  status: string;
  token?: string;
  user: User;
}

const browserAuthHeaders = { 'X-Return-Bearer-Token': 'false' };

export interface MeResponse {
  status: string;
  data: {
    user: User & { is_active: boolean };
    account: Account;
    role: Role;
  };
}

export const authApi = {
  getRegistrationStatus: async (): Promise<{ enabled: boolean }> => {
    const response = await apiClient.get<{ status: string; data: { enabled: boolean } }>(
      '/auth/registration-status',
    );
    return response.data.data;
  },

  login: async (data: LoginFormData): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/auth/login', {
      email: data.email,
      password: data.password,
    }, { headers: browserAuthHeaders });
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/auth/register', data, {
      headers: browserAuthHeaders,
    });
    return response.data;
  },

  getMe: async (): Promise<MeResponse> => {
    const response = await apiClient.get<MeResponse>('/auth/me');
    return response.data;
  },

  updateProfile: async (data: { full_name?: string; phone?: string }) => {
    const response = await apiClient.put<{
      status: string;
      data: User & { is_active: boolean };
    }>('/auth/me', data);
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

  logout: async () => {
    const response = await apiClient.post<{ status: string }>('/auth/logout');
    return response.data;
  },

  deleteAccount: async () => {
    const response = await apiClient.delete<{ message: string }>('/auth/me', {
      data: { confirmation: 'DELETE' },
    });
    return response.data;
  },
};
