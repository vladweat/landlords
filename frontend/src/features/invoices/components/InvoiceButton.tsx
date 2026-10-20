import { useMutation } from '@tanstack/react-query';
import { FileText, RefreshCw } from 'lucide-react';
import { invoicesApi } from '@/features/invoices/api';
import { copyToClipboard } from '@/shared/lib/clipboard';
import { authorizedFetch } from '@/shared/api/client';
import { showError, showSuccess } from '@/shared/lib/toast';
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
      showSuccess(
        `Ссылка на квитанцию скопирована. Действует до ${new Date(data.public_token_expires_at).toLocaleDateString()}`,
      );
      if (data.document_id) {
        try {
          const fileRes = await authorizedFetch(`/api/v1/documents/${data.document_id}`);
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

  const rotateMutation = useMutation({
    mutationFn: () => invoicesApi.rotateShareLink(chargeId),
    onSuccess: async (data) => {
      await copyToClipboard(data.share_url);
      showSuccess(
        `Ссылка перевыпущена, прежняя отключена. Действует до ${new Date(data.public_token_expires_at).toLocaleDateString()}`,
      );
    },
    onError: (error) => showError(error, 'Не удалось перевыпустить ссылку'),
  });

  const isPending = mutation.isPending || rotateMutation.isPending;

  if (!canWrite) return null;

  if (compact) {
    return (
      <div className="inline-flex items-center gap-2">
        <button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={isPending}
          className="text-sm font-medium text-gray-600 hover:text-gray-900 disabled:opacity-50"
        >
          {isPending ? '…' : 'Квитанция'}
        </button>
        <button
          type="button"
          onClick={() => rotateMutation.mutate()}
          disabled={isPending}
          aria-label="Перевыпустить ссылку на квитанцию"
          title="Перевыпустить ссылку"
          className="text-gray-500 hover:text-gray-900 disabled:opacity-50"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="inline-flex flex-wrap gap-2">
      <button
        type="button"
        onClick={() => mutation.mutate()}
        disabled={isPending}
        className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
      >
        <FileText className="h-4 w-4" />
        {isPending ? 'Обработка…' : 'Квитанция'}
      </button>
      <button
        type="button"
        onClick={() => rotateMutation.mutate()}
        disabled={isPending}
        className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
      >
        <RefreshCw className="h-4 w-4" />
        Перевыпустить ссылку
      </button>
    </div>
  );
}
