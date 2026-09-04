import { apiClient } from '@/shared/api/client';
import type { CalendarEventsData } from '@/entities/calendar';

export interface CalendarEventsQuery {
  from?: string;
  to?: string;
}

export const calendarApi = {
  getEvents: async (query?: CalendarEventsQuery): Promise<CalendarEventsData> => {
    const response = await apiClient.get<{ status: string; data: CalendarEventsData }>(
      '/calendar/events',
      { params: query },
    );
    return response.data.data;
  },
};
