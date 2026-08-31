import { LoadingSpinner } from './LoadingSpinner';

export function FullPageLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="text-center">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-sm text-gray-500">Загрузка...</p>
      </div>
    </div>
  );
}
