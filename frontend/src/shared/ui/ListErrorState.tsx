import { AlertTriangle } from 'lucide-react';
import { Button } from './Button';

interface ListErrorStateProps {
  message?: string;
  onRetry?: () => void;
  isRetrying?: boolean;
}

export function ListErrorState({
  message = 'Не удалось загрузить данные',
  onRetry,
  isRetrying = false,
}: ListErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-red-50">
        <AlertTriangle className="h-8 w-8 text-red-400" />
      </div>
      <h3 className="mb-2 text-lg font-semibold text-gray-900">{message}</h3>
      <p className="mb-6 max-w-sm text-sm text-gray-500">
        Проверьте соединение и попробуйте ещё раз
      </p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry} isLoading={isRetrying}>
          Повторить
        </Button>
      )}
    </div>
  );
}
