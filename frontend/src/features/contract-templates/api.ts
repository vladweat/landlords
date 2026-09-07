import { apiClient } from '@/shared/api/client';
import type {
  ContractTemplate,
  ContractTemplateCreatePayload,
  ContractTemplatesListData,
  ContractTemplateUpdatePayload,
} from '@/entities/contractTemplate';

export const contractTemplatesApi = {
  list: async (): Promise<ContractTemplatesListData> => {
    const response = await apiClient.get<{ status: string; data: ContractTemplatesListData }>(
      '/contract-templates',
    );
    return response.data.data;
  },

  create: async (payload: ContractTemplateCreatePayload): Promise<ContractTemplate> => {
    const response = await apiClient.post<{ status: string; data: ContractTemplate }>(
      '/contract-templates',
      payload,
    );
    return response.data.data;
  },

  update: async (
    id: string,
    payload: ContractTemplateUpdatePayload,
  ): Promise<ContractTemplate> => {
    const response = await apiClient.put<{ status: string; data: ContractTemplate }>(
      `/contract-templates/${id}`,
      payload,
    );
    return response.data.data;
  },

  remove: async (id: string): Promise<void> => {
    await apiClient.delete(`/contract-templates/${id}`);
  },
};
