import { apiClient } from '@/shared/api/client';
import type { PaymentClaim, PortalLink, PublicPortal } from '@/entities/portal';

export const portalApi = {
  getPublic: async (token: string): Promise<PublicPortal> => {
    const response = await apiClient.get<{ status: string; data: PublicPortal }>(
      `/public/portal/${token}`,
    );
    return response.data.data;
  },

  createClaim: async (
    token: string,
    body: { charge_id?: string; amount: string; note?: string },
  ): Promise<PaymentClaim> => {
    const response = await apiClient.post<{ status: string; data: PaymentClaim }>(
      `/public/portal/${token}/claim`,
      body,
    );
    return response.data.data;
  },

  ensureLink: async (contractId: string): Promise<PortalLink> => {
    const response = await apiClient.post<{ status: string; data: PortalLink }>(
      `/contracts/${contractId}/portal`,
    );
    return response.data.data;
  },

  rotateLink: async (contractId: string): Promise<PortalLink> => {
    const response = await apiClient.post<{ status: string; data: PortalLink }>(
      `/contracts/${contractId}/portal/rotate`,
    );
    return response.data.data;
  },

  listClaims: async (contractId: string, status?: string): Promise<PaymentClaim[]> => {
    const response = await apiClient.get<{ status: string; data: PaymentClaim[] }>(
      `/contracts/${contractId}/claims`,
      { params: status ? { status } : undefined },
    );
    return response.data.data;
  },

  dismissClaim: async (claimId: string): Promise<PaymentClaim> => {
    const response = await apiClient.post<{ status: string; data: PaymentClaim }>(
      `/claims/${claimId}/dismiss`,
    );
    return response.data.data;
  },

  confirmClaim: async (claimId: string): Promise<PaymentClaim> => {
    const response = await apiClient.post<{ status: string; data: PaymentClaim }>(
      `/claims/${claimId}/confirm`,
    );
    return response.data.data;
  },
};
