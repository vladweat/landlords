import { apiClient } from '@/shared/api/client';
import type { Property } from '@/entities/property';
import type { PaginatedData } from '@/shared/api/types';

export interface PropertyFormData {
  city: string;
  street: string;
  house: string;
  building?: string;
  apartment?: string;
  type: 'apartment' | 'house' | 'commercial';
  size_m2: number;
  purchase_price: number | null;
}

export interface PropertiesQuery {
  page?: number;
  per_page?: number;
  search?: string;
  type?: string;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
}

export const propertiesApi = {
  getAll: async (query?: PropertiesQuery): Promise<PaginatedData<Property>> => {
    const response = await apiClient.get<{ status: string; data: PaginatedData<Property> }>('/properties', { params: query });
    return response.data.data;
  },

  getById: async (id: string): Promise<Property> => {
    const response = await apiClient.get<{ status: string; data: Property }>(`/properties/${id}`);
    return response.data.data;
  },

  create: async (data: PropertyFormData): Promise<Property> => {
    const response = await apiClient.post<{ status: string; data: Property }>('/properties', data);
    return response.data.data;
  },

  update: async (id: string, data: PropertyFormData): Promise<Property> => {
    const response = await apiClient.put<{ status: string; data: Property }>(`/properties/${id}`, data);
    return response.data.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/properties/${id}`);
  },
};
