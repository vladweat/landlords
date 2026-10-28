import { apiClient } from '@/shared/api/client';
import type {
  Account,
  CheckoutResult,
  Invite,
  InvitePreview,
  Member,
  PlanId,
  Role,
  Subscription,
} from '@/entities/account';
import type { AuthData, AuthResponse } from '@/features/auth/api';

export const accountApi = {
  get: async (): Promise<Account> => {
    const response = await apiClient.get<{ status: string; data: Account }>('/account');
    return response.data.data;
  },

  getSubscription: async (): Promise<Subscription> => {
    const response = await apiClient.get<{ status: string; data: Subscription }>(
      '/account/subscription',
    );
    return response.data.data;
  },

  changePlan: async (plan: PlanId | string): Promise<Account> => {
    const response = await apiClient.patch<{ status: string; data: Account }>(
      '/account/plan',
      { plan },
    );
    return response.data.data;
  },

  createCheckout: async (): Promise<CheckoutResult> => {
    const response = await apiClient.post<{ status: string; data: CheckoutResult }>(
      '/billing/checkout',
    );
    return response.data.data;
  },

  confirmPayment: async (
    paymentId: string,
  ): Promise<{ status: string; account_id?: string | null; reason?: string | null }> => {
    const response = await apiClient.post<{
      status: string;
      data: { status: string; account_id?: string | null; reason?: string | null };
    }>('/billing/confirm', { payment_id: paymentId });
    return response.data.data;
  },

  cancelSubscription: async (): Promise<{
    id: string;
    plan: string;
    subscription_status: string;
    subscription_period_end?: string | null;
  }> => {
    const response = await apiClient.post<{
      status: string;
      data: {
        id: string;
        plan: string;
        subscription_status: string;
        subscription_period_end?: string | null;
      };
    }>('/billing/cancel');
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
  ): Promise<AuthData> => {
    const response = await apiClient.post<AuthResponse>(
      `/public/invites/${token}/accept`,
      data,
      { headers: { 'X-Return-Bearer-Token': 'false' } },
    );
    return response.data.data;
  },

  exportData: async (): Promise<void> => {
    const response = await apiClient.get('/account/export', {
      responseType: 'blob',
    });
    const header = response.headers['content-disposition'] as string | undefined;
    const match = header ? /filename="?([^"]+)"?/i.exec(header) : null;
    const filename = match?.[1] || 'landlords_export.zip';
    const url = window.URL.createObjectURL(response.data as Blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },
};
