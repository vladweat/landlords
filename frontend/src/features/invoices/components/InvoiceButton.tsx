import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { FileText } from 'lucide-react';
import { invoicesApi } from '@/features/invoices/api';
import { copyToClipboard } from '@/shared/lib/clipboard';
import { showError } from '@/shared/lib/toast';
import { useCan } from '@/features/auth/permissions';

interface InvoiceButtonProps {
  chargeId: string;
  compact?: boolean;
}

/** Создать/обновить квитанцию, скопировать публичную ссылку. */
export function InvoiceButton({ chargeId, compact }: InvoiceButtonProps) {
  const canWrite = useCan('write_charges');

  const mutation = useMutation({
    mutationFn: () => invoicesApi.ensure(chargeId),
    onSuccess: async (data) => {
      await copyToClipboard(data.share_url);
      toast.success('Ссылка на квитанцию скопирована');
      if (data.document_id) {
        try {
          const token = localStorage.getItem('access_token');
          const fileRes = await fetch(`/api/v1/documents/${data.document_id}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          });
          if (fileRes.ok) {
            const blob = await fileRes.blob();
            window.open(URL.createObjectURL(blob), '_blank');
          }
        } catch {
          // ссылка уже скопирована — PDF опционален
        }
      }
    },
    onError: (error) => showError(error, 'Не удалось создать квитанцию'),
  });

  if (!canWrite) return null;

  if (compact) {
    return (
      <button
        type="button"
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="text-sm font-medium text-gray-600 hover:text-gray-900 disabled:opacity-50"
      >
        {mutation.isPending ? '…' : 'Квитанция'}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={() => mutation.mutate()}
      disabled={mutation.isPending}
      className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
    >
      <FileText className="h-4 w-4" />
      {mutation.isPending ? 'Создание…' : 'Квитанция'}
    </button>
  );
}
