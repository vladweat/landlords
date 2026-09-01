import { apiClient } from '@/shared/api/client';
import type { Contract, Ledger, EventsResponse } from '@/entities/contract';
import type { PaginatedData } from '@/shared/api/types';

export interface ContractFormData {
  property_id: string;
  tenant_id: string;
  rent_amount: string;
  currency: string;
  start_date: string;
  end_date: string;
  payment_day: number;
  billing_period: string;
  deposit_amount: string | null;
  auto_generate_charges: boolean;
}

export interface ContractUpdateData extends Partial<ContractFormData> {
  status?: Contract['status'];
  termination_reason?: string | null;
}

export interface ContractsQuery {
  page?: number;
  per_page?: number;
  overdue_only?: boolean;
  search?: string;
  status?: string;
}

export interface TerminateContractData {
  effective_date: string;
  termination_reason: string;
  generate_act?: boolean;
}

export interface RenewContractData {
  new_end_date: string;
  new_rent_amount?: string | null;
  generate_act?: boolean;
}

export interface ContractLifecycleResult {
  contract: Contract;
  charges_deleted: number;
  charges_updated: number;
  charges_created: number;
  document_id: string | null;
  document_url: string | null;
  document_filename: string | null;
}

export const contractsApi = {
  getAll: async (query?: ContractsQuery): Promise<PaginatedData<Contract>> => {
    const response = await apiClient.get<{ status: string; data: PaginatedData<Contract> }>('/contracts', { params: query });
    return response.data.data;
  },

  getById: async (id: string): Promise<Contract> => {
    const response = await apiClient.get<{ status: string; data: Contract }>(`/contracts/${id}`);
    return response.data.data;
  },

  getLedger: async (id: string): Promise<Ledger> => {
    const response = await apiClient.get<{ status: string; data: Ledger }>(`/contracts/${id}/ledger`);
    return response.data.data;
  },

  getEvents: async (id: string, page = 1, perPage = 10): Promise<EventsResponse> => {
    const response = await apiClient.get<{ status: string; data: EventsResponse }>(`/contracts/${id}/events`, { params: { page, per_page: perPage } });
    return response.data.data;
  },

  createNote: async (contractId: string, title: string, description?: string) => {
    const response = await apiClient.post<{ status: string; data: { id: string } }>(`/contracts/${contractId}/events`, { title, description: description || null });
    return response.data.data;
  },

  generateCharges: async (id: string): Promise<{ task_id: string }> => {
    const response = await apiClient.post<{ status: string; data: { task_id: string } }>(`/contracts/${id}/generate-charges`);
    return response.data.data;
  },

  refreshStatus: async (id: string): Promise<{ id: string; status: string }> => {
    const response = await apiClient.post<{ status: string; data: { id: string; status: string } }>(`/contracts/${id}/refresh-status`);
    return response.data.data;
  },

  create: async (data: ContractFormData): Promise<Contract> => {
    const response = await apiClient.post<{ status: string; data: Contract }>('/contracts', data);
    return response.data.data;
  },

  update: async (id: string, data: ContractUpdateData): Promise<Contract> => {
    const response = await apiClient.put<{ status: string; data: Contract }>(`/contracts/${id}`, data);
    return response.data.data;
  },

  terminate: async (id: string, data: TerminateContractData): Promise<ContractLifecycleResult> => {
    const response = await apiClient.post<{ status: string; data: ContractLifecycleResult }>(
      `/contracts/${id}/terminate`,
      data,
    );
    return response.data.data;
  },

  renew: async (id: string, data: RenewContractData): Promise<ContractLifecycleResult> => {
    const response = await apiClient.post<{ status: string; data: ContractLifecycleResult }>(
      `/contracts/${id}/renew`,
      data,
    );
    return response.data.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/contracts/${id}`);
  },
};
