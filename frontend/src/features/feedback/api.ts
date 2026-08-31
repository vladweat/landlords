import { apiClient } from '@/shared/api/client';

export type FeedbackCategory = 'bug' | 'feature' | 'question' | 'other';

export interface FeedbackRequest {
  category: FeedbackCategory;
  message: string;
}

export const feedbackApi = {
  send: async (data: FeedbackRequest) => {
    const response = await apiClient.post<{ status: string; data: { id: string; message: string } }>('/feedback', data);
    return response.data;
  },
};
