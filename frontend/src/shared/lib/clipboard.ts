export async function copyToClipboard(text: string, showToast = true) {
  await navigator.clipboard.writeText(text);
  if (showToast) {
    const { toast } = await import('sonner');
    toast.success('Скопировано');
  }
}
