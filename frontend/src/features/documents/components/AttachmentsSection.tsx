import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, FileText, Paperclip, Plus, Trash2 } from 'lucide-react';
import { documentsApi } from '@/features/documents/api';
import {
  DOCUMENT_CATEGORY_LABELS,
  UPLOAD_CATEGORY_OPTIONS,
  type UploadDocumentCategory,
} from '@/entities/document';
import { authorizedFetch } from '@/shared/api/client';
import { showError, showSuccess } from '@/shared/lib/toast';
import { formatDate } from '@/shared/lib/utils';
import { Button } from '@/shared/ui/Button';
import { Card } from '@/shared/ui/Card';
import { EmptyState } from '@/shared/ui/EmptyState';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { TableSkeleton } from '@/shared/ui/Skeleton';
import { useCan } from '@/features/auth/permissions';

interface AttachmentsSectionProps {
  parentType: 'contract' | 'property';
  parentId: string;
}

function formatSize(bytes: number | null): string {
  if (bytes == null) return '—';
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}

export function AttachmentsSection({ parentType, parentId }: AttachmentsSectionProps) {
  const queryClient = useQueryClient();
  const canWrite = useCan('write_documents');
  const fileRef = useRef<HTMLInputElement>(null);
  const [category, setCategory] = useState<UploadDocumentCategory>('other');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const queryKey =
    parentType === 'contract'
      ? ['contract-documents', parentId]
      : ['property-documents', parentId];

  const { data: docs, isLoading } = useQuery({
    queryKey,
    queryFn: () =>
      parentType === 'contract'
        ? documentsApi.listByContract(parentId)
        : documentsApi.listByProperty(parentId),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      parentType === 'contract'
        ? documentsApi.uploadForContract(parentId, { file, category })
        : documentsApi.uploadForProperty(parentId, { file, category }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      showSuccess('Файл загружен');
      if (fileRef.current) fileRef.current.value = '';
    },
    onError: (error) => showError(error, 'Ошибка загрузки'),
  });

  const deleteMutation = useMutation({
    mutationFn: documentsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      setDeletingId(null);
      showSuccess('Файл удалён');
    },
    onError: (error) => showError(error, 'Ошибка удаления'),
  });

  const openDownload = (url: string) => {
    void (async () => {
      try {
        const res = await authorizedFetch(url);
        if (!res.ok) throw new Error('download failed');
        const blob = await res.blob();
        const objectUrl = URL.createObjectURL(blob);
        window.open(objectUrl, '_blank');
        setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
      } catch (error) {
        showError(error, 'Не удалось скачать файл');
      }
    })();
  };

  return (
    <Card>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-3">
        <h2 className="text-lg font-medium text-gray-800">Документы</h2>
        {canWrite && (
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as UploadDocumentCategory)}
              className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {UPLOAD_CATEGORY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) uploadMutation.mutate(file);
              }}
            />
            <Button
              size="sm"
              leftIcon={<Plus className="h-4 w-4" />}
              onClick={() => fileRef.current?.click()}
              disabled={uploadMutation.isPending}
            >
              {uploadMutation.isPending ? 'Загрузка…' : 'Загрузить'}
            </Button>
          </div>
        )}
      </div>

      {isLoading ? (
        <TableSkeleton rows={3} cols={4} />
      ) : !docs?.length ? (
        <EmptyState
          icon={Paperclip}
          title="Нет документов"
          description="Загрузите сканы паспорта, акты или фото объекта"
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wide text-gray-500 border-b">
                <th className="py-2 text-left font-medium">Название</th>
                <th className="py-2 text-left font-medium">Категория</th>
                <th className="py-2 text-left font-medium hidden sm:table-cell">Размер</th>
                <th className="py-2 text-left font-medium hidden sm:table-cell">Дата</th>
                <th className="py-2 text-right font-medium w-20"></th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc) => (
                <tr key={doc.id} className="border-b last:border-0">
                  <td className="py-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText className="h-4 w-4 text-gray-400 shrink-0" />
                      <span className="truncate">{doc.title || doc.filename}</span>
                      {doc.source === 'generated' && (
                        <span className="text-xs text-gray-400 shrink-0">авто</span>
                      )}
                    </div>
                  </td>
                  <td className="py-2 text-gray-600">
                    {DOCUMENT_CATEGORY_LABELS[doc.category] || doc.category}
                  </td>
                  <td className="py-2 text-gray-500 hidden sm:table-cell">
                    {formatSize(doc.size_bytes)}
                  </td>
                  <td className="py-2 text-gray-500 hidden sm:table-cell">
                    {doc.created_at ? formatDate(doc.created_at) : '—'}
                  </td>
                  <td className="py-2">
                    <div className="flex justify-end gap-1">
                      <button
                        type="button"
                        onClick={() => openDownload(doc.url)}
                        className="p-1.5 text-gray-400 hover:text-blue-600 rounded"
                        title="Скачать"
                      >
                        <Download className="h-4 w-4" />
                      </button>
                      {doc.source === 'uploaded' && canWrite && (
                        <button
                          type="button"
                          onClick={() => setDeletingId(doc.id)}
                          className="p-1.5 text-gray-400 hover:text-red-600 rounded"
                          title="Удалить"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmDialog
        isOpen={!!deletingId}
        onClose={() => setDeletingId(null)}
        onConfirm={() => deletingId && deleteMutation.mutate(deletingId)}
        title="Удалить файл?"
        message="Файл будет удалён безвозвратно."
        isLoading={deleteMutation.isPending}
      />
    </Card>
  );
}
