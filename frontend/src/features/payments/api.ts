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

export interface PaymentCreateResult {
  payments: Payment[];
  total_amount: string;
}

export const paymentsApi = {
  getAll: async (): Promise<Payment[]> => {
    const response = await apiClient.get<{ status: string; data: Payment[] }>('/payments');
    return response.data.data;
  },

  create: async (data: PaymentFormData, idempotencyKey: string): Promise<PaymentCreateResult> => {
    const response = await apiClient.post<{ status: string; data: PaymentCreateResult }>(
      '/payments',
      data,
      { headers: { 'Idempotency-Key': idempotencyKey } },
    );
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
