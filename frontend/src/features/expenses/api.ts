import { apiClient } from '@/shared/api/client';
import type { ExpenseCategory, PropertyExpense } from '@/entities/expense';

export interface ExpenseFormData {
  property_id: string;
  category: ExpenseCategory;
  amount: string;
  date_incurred: string;
  note?: string;
}

export const expensesApi = {
  getAll: async (propertyId?: string): Promise<PropertyExpense[]> => {
    const response = await apiClient.get<{ status: string; data: PropertyExpense[] }>(
      '/expenses',
      { params: propertyId ? { property_id: propertyId } : undefined },
    );
    return response.data.data;
  },

  create: async (data: ExpenseFormData): Promise<PropertyExpense> => {
    const response = await apiClient.post<{ status: string; data: PropertyExpense }>(
      '/expenses',
      data,
    );
    return response.data.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/expenses/${id}`);
  },
};
