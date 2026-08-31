import { useState } from 'react';
import { FileDown } from 'lucide-react';
import { apiClient } from '@/shared/api/client';
import { showError } from '@/shared/lib/toast';

interface DownloadContractButtonProps {
  contractId: string;
}

export function DownloadContractButton({ contractId }: DownloadContractButtonProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleDownload = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get<{ status: string; data: { url: string; filename: string } }>(
        `/contracts/${contractId}/document`
      );
      const { url } = response.data.data;
      window.open(url, '_blank');
    } catch (error) {
      showError(error, 'Ошибка скачивания');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      onClick={handleDownload}
      disabled={isLoading}
      className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
    >
      {isLoading ? (
        <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
      ) : (
        <FileDown className="h-4 w-4" />
      )}
      Скачать договор
    </button>
  );
}
