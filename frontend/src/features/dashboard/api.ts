import { apiClient } from '@/shared/api/client';
import type { DashboardSummary } from '@/entities/payment';
import type { ForecastResponse, PropertyOverview, LastPayment } from '@/entities/dashboard';

export const dashboardApi = {
  getSummary: async (): Promise<DashboardSummary> => {
    const response = await apiClient.get<{ status: string; data: DashboardSummary }>('/dashboard/summary');
    return response.data.data;
  },

  getForecast: async (): Promise<ForecastResponse> => {
    const response = await apiClient.get<{ status: string; data: ForecastResponse }>('/dashboard/forecast');
    return response.data.data;
  },

  getPropertiesOverview: async (): Promise<PropertyOverview[]> => {
    const response = await apiClient.get<{ status: string; data: PropertyOverview[] }>('/dashboard/properties-overview');
    return response.data.data;
  },

  getLastPayments: async (limit = 5): Promise<LastPayment[]> => {
    const response = await apiClient.get<{ status: string; data: LastPayment[] }>('/dashboard/last-payments', {
      params: { limit },
    });
    return response.data.data;
  },
};
