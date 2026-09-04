import { apiClient } from '@/shared/api/client';
import type { DocumentItem, UploadDocumentCategory } from '@/entities/document';

export interface UploadDocumentParams {
  file: File;
  title?: string;
  category?: UploadDocumentCategory;
}

function toFormData({ file, title, category }: UploadDocumentParams): FormData {
  const form = new FormData();
  form.append('file', file);
  if (title) form.append('title', title);
  if (category) form.append('category', category);
  return form;
}

export const documentsApi = {
  listByContract: async (contractId: string): Promise<DocumentItem[]> => {
    const response = await apiClient.get<{ status: string; data: DocumentItem[] }>(
      `/contracts/${contractId}/documents`,
    );
    return response.data.data;
  },

  listByProperty: async (propertyId: string): Promise<DocumentItem[]> => {
    const response = await apiClient.get<{ status: string; data: DocumentItem[] }>(
      `/properties/${propertyId}/documents`,
    );
    return response.data.data;
  },

  uploadForContract: async (
    contractId: string,
    params: UploadDocumentParams,
  ): Promise<DocumentItem> => {
    const response = await apiClient.post<{ status: string; data: DocumentItem }>(
      `/contracts/${contractId}/documents`,
      toFormData(params),
    );
    return response.data.data;
  },

  uploadForProperty: async (
    propertyId: string,
    params: UploadDocumentParams,
  ): Promise<DocumentItem> => {
    const response = await apiClient.post<{ status: string; data: DocumentItem }>(
      `/properties/${propertyId}/documents`,
      toFormData(params),
    );
    return response.data.data;
  },

  delete: async (docId: string): Promise<void> => {
    await apiClient.delete(`/documents/${docId}`);
  },

  downloadUrl: (docId: string): string => `/api/v1/documents/${docId}`,
};
