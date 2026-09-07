import { apiClient } from '@/shared/api/client';
import type { Invoice, PublicInvoice } from '@/entities/invoice';

export const invoicesApi = {
  ensure: async (chargeId: string): Promise<Invoice> => {
    const response = await apiClient.post<{ status: string; data: Invoice }>(
      `/charges/${chargeId}/invoice`,
    );
    return response.data.data;
  },

  getByCharge: async (chargeId: string): Promise<Invoice> => {
    const response = await apiClient.get<{ status: string; data: Invoice }>(
      `/charges/${chargeId}/invoice`,
    );
    return response.data.data;
  },

  getPublic: async (token: string): Promise<PublicInvoice> => {
    const response = await apiClient.get<{ status: string; data: PublicInvoice }>(
      `/public/invoices/${token}`,
    );
    return response.data.data;
  },

  publicPdfUrl: (token: string): string => `/api/v1/public/invoices/${token}/pdf`,
};
