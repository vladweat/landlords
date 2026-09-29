import { apiClient } from '@/shared/api/client';
import type { Account, Invite, InvitePreview, Member, Role } from '@/entities/account';
import type { AuthResponse } from '@/features/auth/api';

export const accountApi = {
  get: async (): Promise<Account> => {
    const response = await apiClient.get<{ status: string; data: Account }>('/account');
    return response.data.data;
  },

  update: async (data: {
    name?: string;
    base_currency?: string;
    timezone?: string;
    payment_details?: string | null;
  }): Promise<Account> => {
    const response = await apiClient.patch<{ status: string; data: Account }>('/account', data);
    return response.data.data;
  },

  listMembers: async (): Promise<Member[]> => {
    const response = await apiClient.get<{ status: string; data: Member[] }>('/account/members');
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

  listInvites: async (): Promise<Invite[]> => {
    const response = await apiClient.get<{ status: string; data: Invite[] }>('/account/invites');
    return response.data.data;
  },

  createInvite: async (data: {
    email: string;
    full_name: string;
    role: Exclude<Role, 'owner'>;
  }): Promise<Invite> => {
    const response = await apiClient.post<{ status: string; data: Invite }>(
      '/account/invites',
      data,
    );
    return response.data.data;
  },

  revokeInvite: async (inviteId: string): Promise<void> => {
    await apiClient.delete(`/account/invites/${inviteId}`);
  },

  getInvitePreview: async (token: string): Promise<InvitePreview> => {
    const response = await apiClient.get<{ status: string; data: InvitePreview }>(
      `/public/invites/${token}`,
    );
    return response.data.data;
  },

  acceptInvite: async (
    token: string,
    data: { password: string; full_name?: string },
  ): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>(
      `/public/invites/${token}/accept`,
      data,
    );
    return response.data;
  },
};
