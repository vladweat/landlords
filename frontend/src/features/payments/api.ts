import { apiClient } from '@/shared/api/client';
import type { Payment } from '@/entities/payment';

export interface PaymentFormData {
  contract_id: string;
  amount: string;
  date_paid: string;
  method: string;
  note?: string;
  rent_charge_id?: string;
}

export const paymentsApi = {
  getAll: async (): Promise<Payment[]> => {
    const response = await apiClient.get<{ status: string; data: Payment[] }>('/payments');
    return response.data.data;
  },

  create: async (data: PaymentFormData): Promise<Payment> => {
    const response = await apiClient.post<{ status: string; data: Payment }>('/payments', data);
    return response.data.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/payments/${id}`);
  },

  getCharges: async (contractId: string) => {
    const response = await apiClient.get(`/charges/contracts/${contractId}/charges`);
    return response.data.data;
  },
};
