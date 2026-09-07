import { apiClient } from '@/shared/api/client';
import type { NotificationsData } from '@/entities/notification';

export const notificationsApi = {
  list: async (): Promise<NotificationsData> => {
    const response = await apiClient.get<{ status: string; data: NotificationsData }>(
      '/notifications',
    );
    return response.data.data;
  },

  dismiss: async (notificationKey: string): Promise<void> => {
    await apiClient.post('/notifications/dismiss', {
      notification_key: notificationKey,
    });
  },
};
