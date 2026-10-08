import { showSuccess } from '@/shared/lib/toast';
export async function copyToClipboard(text: string, showToast = true) {
  await navigator.clipboard.writeText(text);
  if (showToast) {
    showSuccess('Скопировано');
  }
}
