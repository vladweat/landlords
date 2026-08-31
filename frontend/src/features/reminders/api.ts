import { apiClient } from '@/shared/api/client';
import type { ReminderResponse, ReminderRequest } from './types';

export const remindersApi = {
  create: async (data: ReminderRequest): Promise<ReminderResponse> => {
    const response = await apiClient.post<{ status: string; data: ReminderResponse }>('/reminders', data);
    return response.data.data;
  },

  getByCharge: async (chargeId: string): Promise<ReminderResponse[]> => {
    const response = await apiClient.get<{ status: string; data: ReminderResponse[] }>(`/reminders/${chargeId}`);
    return response.data.data;
  },
};
