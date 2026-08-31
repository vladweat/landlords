import { toast } from 'sonner';
import type { AxiosError } from 'axios';
import { getUserMessage } from './errorMessages';

export const showSuccess = (message: string) => toast.success(message);

export const showUndo = (message: string, onUndo: () => void) => {
  toast(message, { action: { label: 'Отменить', onClick: onUndo }, duration: 5000 });
};

export const showError = (error: unknown, fallback = 'Произошла ошибка'): void => {
  const message = extractErrorMessage(error, fallback);
  toast.error(message);
};

function extractErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error) {
    const axiosError = error as AxiosError<{ detail?: { msg?: string }[] | string }>;
    const detail = axiosError.response?.data?.detail;

    if (typeof detail === 'string') return getUserMessage(detail);
    if (Array.isArray(detail) && detail.length > 0 && detail[0].msg) return getUserMessage(detail[0].msg);
    if (axiosError.message) return getUserMessage(axiosError.message);
  }
  return fallback;
}
