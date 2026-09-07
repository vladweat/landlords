import { apiClient } from '@/shared/api/client';

export type ReportFormat = 'xlsx' | 'csv';

export interface ReportExportParams {
  start_date: string;
  end_date: string;
  format: ReportFormat;
}

function filenameFromDisposition(header: string | undefined, fallback: string): string {
  if (!header) return fallback;
  const match = /filename="?([^"]+)"?/i.exec(header);
  return match?.[1] || fallback;
}

export const reportsApi = {
  export: async (params: ReportExportParams): Promise<void> => {
    const response = await apiClient.get('/reports/export', {
      params,
      responseType: 'blob',
    });
    const fallback = `report_${params.start_date}_${params.end_date}.${params.format}`;
    const filename = filenameFromDisposition(
      response.headers['content-disposition'] as string | undefined,
      fallback,
    );
    const url = window.URL.createObjectURL(response.data as Blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },
};
