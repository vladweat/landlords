import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from './Button';

interface ListPaginationProps {
  page: number;
  pages: number;
  total: number;
  onPageChange: (page: number) => void;
  /** Подпись сущности во множественном числе, напр. «объектов». */
  entityLabel?: string;
}

/** Показывается только при нескольких страницах — без дубля счётчика на одной странице. */
export function ListPagination({
  page,
  pages,
  total,
  onPageChange,
  entityLabel = 'записей',
}: ListPaginationProps) {
  if (pages <= 1) return null;

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between pt-1">
      <p className="text-sm text-gray-500">
        {total.toLocaleString('ru-RU')} {entityLabel} · стр. {page} из {pages}
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          leftIcon={<ChevronLeft className="h-4 w-4" />}
          aria-label="Предыдущая страница"
        >
          Назад
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pages}
          rightIcon={<ChevronRight className="h-4 w-4" />}
          aria-label="Следующая страница"
        >
          Вперёд
        </Button>
      </div>
    </div>
  );
}
