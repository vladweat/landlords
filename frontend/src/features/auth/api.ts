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
  status: 'success';
  data: {
    token?: string;
    user: User;
  };
}

export interface AuthData {
  token?: string;
  user: User;
}

type MessageResponse = {
  status: 'success';
  data: { message: string };
};

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

  login: async (data: LoginFormData): Promise<AuthData> => {
    const response = await apiClient.post<AuthResponse>('/auth/login', {
      email: data.email,
      password: data.password,
    }, { headers: browserAuthHeaders });
    return response.data.data;
  },

  register: async (data: RegisterRequest): Promise<AuthData> => {
    const response = await apiClient.post<AuthResponse>('/auth/register', data, {
      headers: browserAuthHeaders,
    });
    return response.data.data;
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
    return response.data.data;
  },

  changePassword: async (data: { current_password: string; new_password: string }) => {
    const response = await apiClient.post<MessageResponse>('/auth/change-password', data);
    return response.data.data;
  },

  forgotPassword: async (email: string) => {
    const response = await apiClient.post<MessageResponse>('/auth/forgot-password', { email });
    return response.data.data;
  },

  resetPassword: async (data: { token: string; new_password: string }) => {
    const response = await apiClient.post<MessageResponse>('/auth/reset-password', data);
    return response.data.data;
  },

  logout: async () => {
    const response = await apiClient.post<{ status: string; data: Record<string, never> }>('/auth/logout');
    return response.data.data;
  },

  deleteAccount: async () => {
    const response = await apiClient.delete<MessageResponse>('/auth/me', {
      data: { confirmation: 'DELETE' },
    });
    return response.data.data;
  },
};
