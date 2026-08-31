import { Link } from 'react-router-dom';
import { Home } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-200 mb-4">404</h1>
        <p className="text-lg text-gray-600 mb-2">Страница не найдена</p>
        <p className="text-sm text-gray-400 mb-6">Запрашиваемая страница не существует</p>
        <Link to="/dashboard" className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          <Home className="h-4 w-4" /> На дашборд
        </Link>
      </div>
    </div>
  );
}
