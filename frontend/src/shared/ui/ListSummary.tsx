interface ListSummaryProps {
  total: number;
  entityLabel: string;
  /** Краткое описание активных фильтров, напр. «поиск + тип». Без фильтра блок скрыт. */
  filterHint?: string | null;
}

/** Счётчик только при активных фильтрах — иначе дублирует пагинацию / пустой экран. */
export function ListSummary({ total, entityLabel, filterHint }: ListSummaryProps) {
  if (!filterHint) return null;

  return (
    <p className="text-sm text-gray-500">
      Найдено: {total.toLocaleString('ru-RU')} {entityLabel}
      <span className="text-gray-400"> · {filterHint}</span>
    </p>
  );
}
