import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileDown } from 'lucide-react';
import { apiClient } from '@/shared/api/client';
import { showError } from '@/shared/lib/toast';
import { contractTemplatesApi } from '@/features/contract-templates/api';
import { Button } from '@/shared/ui/Button';

interface DownloadContractButtonProps {
  contractId: string;
}

export function DownloadContractButton({ contractId }: DownloadContractButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [templateId, setTemplateId] = useState('');

  const { data } = useQuery({
    queryKey: ['contract-templates'],
    queryFn: contractTemplatesApi.list,
  });

  const templates = data?.items ?? [];
  const showPicker = templates.length > 1;

  const handleDownload = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get<{
        status: string;
        data: { url: string; filename: string };
      }>(`/contracts/${contractId}/document`, {
        params: templateId ? { template_id: templateId } : undefined,
      });
      const { url } = response.data.data;
      window.open(url, '_blank');
    } catch (error) {
      showError(error, 'Ошибка скачивания');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="inline-flex flex-wrap items-center gap-2">
      {showPicker && (
        <select
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
          value={templateId}
          onChange={(e) => setTemplateId(e.target.value)}
        >
          <option value="">Шаблон по умолчанию</option>
          {templates.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
              {t.is_default ? ' ★' : ''}
            </option>
          ))}
        </select>
      )}
      <Button
        onClick={() => void handleDownload()}
        isLoading={isLoading}
        leftIcon={<FileDown className="h-4 w-4" />}
      >
        Скачать договор
      </Button>
    </div>
  );
}
