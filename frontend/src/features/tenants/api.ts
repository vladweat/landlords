import { apiClient } from '@/shared/api/client';
import type { Tenant } from '@/entities/tenant';
import type { PaginatedData } from '@/shared/api/types';
import type { TenantScore } from './types';

export interface TenantFormData {
  full_name: string;
  email: string;
  phone: string;
}

export interface TenantsQuery {
  page?: number;
  per_page?: number;
  search?: string;
  include_score?: boolean;
}

export const tenantsApi = {
  getAll: async (query?: TenantsQuery): Promise<PaginatedData<Tenant>> => {
    const response = await apiClient.get<{ status: string; data: PaginatedData<Tenant> }>('/tenants', { params: query });
    return response.data.data;
  },

  getScore: async (id: string): Promise<TenantScore> => {
    const response = await apiClient.get<{ status: string; data: TenantScore }>(`/tenants/${id}/score`);
    return response.data.data;
  },

  create: async (data: TenantFormData): Promise<Tenant> => {
    const response = await apiClient.post<{ status: string; data: Tenant }>('/tenants', data);
    return response.data.data;
  },

  update: async (id: string, data: TenantFormData): Promise<Tenant> => {
    const response = await apiClient.put<{ status: string; data: Tenant }>(`/tenants/${id}`, data);
    return response.data.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/tenants/${id}`);
  },
};
