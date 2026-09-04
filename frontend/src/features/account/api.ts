import { apiClient } from '@/shared/api/client';
import type { Account, Member, Role } from '@/entities/account';

export const accountApi = {
  get: async (): Promise<Account> => {
    const response = await apiClient.get<{ status: string; data: Account }>('/account');
    return response.data.data;
  },

  update: async (data: {
    name?: string;
    base_currency?: string;
    timezone?: string;
  }): Promise<Account> => {
    const response = await apiClient.patch<{ status: string; data: Account }>('/account', data);
    return response.data.data;
  },

  listMembers: async (): Promise<Member[]> => {
    const response = await apiClient.get<{ status: string; data: Member[] }>('/account/members');
    return response.data.data;
  },

  createMember: async (data: {
    email: string;
    full_name: string;
    password: string;
    role: Exclude<Role, 'owner'>;
  }): Promise<Member> => {
    const response = await apiClient.post<{ status: string; data: Member }>(
      '/account/members',
      data,
    );
    return response.data.data;
  },

  updateMemberRole: async (userId: string, role: Exclude<Role, 'owner'>): Promise<Member> => {
    const response = await apiClient.patch<{ status: string; data: Member }>(
      `/account/members/${userId}`,
      { role },
    );
    return response.data.data;
  },

  removeMember: async (userId: string): Promise<void> => {
    await apiClient.delete(`/account/members/${userId}`);
  },
};
