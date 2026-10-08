import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Trash2, Wallet, Search } from 'lucide-react';
import { showError, showSuccess } from '@/shared/lib/toast';
import { formatDate } from '@/shared/lib/utils';
import { scrollToTop } from '@/shared/lib/scrollToTop';
import { expensesApi } from '@/features/expenses/api';
import { propertiesApi } from '@/features/properties/api';
import type { PropertyExpense } from '@/entities/expense';
import { EXPENSE_CATEGORY_LABELS } from '@/entities/expense';
import { Button } from '@/shared/ui/Button';
import { EmptyState } from '@/shared/ui/EmptyState';
import { ActionMenu } from '@/shared/ui/ActionMenu';
import { ListErrorState } from '@/shared/ui/ListErrorState';
import { ListSummary } from '@/shared/ui/ListSummary';
import { MobileList, MobileListItem } from '@/shared/ui/MobileList';
import { ExpenseModal } from '@/features/expenses/components/ExpenseModal';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { useHotkeys } from '@/shared/hooks/useHotkeys';
import { useSort } from '@/shared/hooks/useSort';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { useCan } from '@/features/auth/permissions';
import { TableSkeleton } from '@/shared/ui/Skeleton';
import { shortAddress } from '@/shared/lib/address';

export default function ExpensesPage() {
  const queryClient = useQueryClient();
  const canWrite = useCan('write_expenses');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [deleting, setDeleting] = useState<PropertyExpense | null>(null);
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search, 300);
  useHotkeys(canWrite ? { n: () => setIsModalOpen(true) } : {});

  const { data: expenses, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: ['expenses'],
    queryFn: () => expensesApi.getAll(),
  });
  const { data: propertiesData } = useQuery({
    queryKey: ['properties'],
    queryFn: () => propertiesApi.getAll({ per_page: 100 }),
    staleTime: 10 * 60 * 1000,
  });
  const properties = propertiesData?.items || [];

  const propertyMap = useMemo(() => {
    const m: Record<string, { label: string; href: string }> = {};
    properties.forEach((p) => {
      m[p.id] = { label: shortAddress(p.address), href: `/properties/${p.id}` };
    });
    return m;
  }, [properties]);

  const filtered = useMemo(() => {
    if (!expenses) return [];
    if (!debouncedSearch) return expenses;
    const q = debouncedSearch.toLowerCase();
    return expenses.filter((e) => {
      const address = (propertyMap[e.property_id]?.label || '').toLowerCase();
      const category = (EXPENSE_CATEGORY_LABELS[e.category] || e.category).toLowerCase();
      return (
        address.includes(q) ||
        category.includes(q) ||
        (e.note || '').toLowerCase().includes(q)
      );
    });
  }, [expenses, debouncedSearch, propertyMap]);

  const { sorted, sortKey, sortDir, toggle } = useSort(filtered);
  const hasSource = (expenses?.length ?? 0) > 0;
  const emptyAfterFilter = hasSource && filtered.length === 0;

  const deleteMutation = useMutation({
    mutationFn: expensesApi.delete,
    onSuccess: () => {
      scrollToTop();
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
      queryClient.invalidateQueries({ queryKey: ['properties'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      setDeleting(null);
      showSuccess('Расход удалён');
    },
    onError: (error) => showError(error, 'Ошибка удаления'),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Расходы</h1>
          <p className="mt-1 text-sm text-gray-500">ЖКХ, ремонт, налоги и прочие затраты</p>
        </div>
        {canWrite && (
          <Button onClick={() => setIsModalOpen(true)} leftIcon={<Plus className="h-4 w-4" />}>
            Добавить
          </Button>
        )}
      </div>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          aria-label="Поиск по объекту или категории"
          placeholder="Поиск по объекту, категории..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {isLoading ? (
        <TableSkeleton rows={5} cols={5} />
      ) : isError ? (
        <ListErrorState onRetry={() => void refetch()} isRetrying={isFetching} />
      ) : !hasSource ? (
        <EmptyState
          icon={Wallet}
          title="Нет расходов"
          description="Учитывайте ЖКХ, ремонт, налоги и комиссию — ROI станет точнее"
          action={
            canWrite
              ? { label: 'Добавить расход', onClick: () => setIsModalOpen(true) }
              : undefined
          }
        />
      ) : emptyAfterFilter ? (
        <EmptyState
          icon={Wallet}
          title="Ничего не найдено"
          description="Измените параметры поиска"
        />
      ) : (
        <>
          <ListSummary
            total={filtered.length}
            entityLabel="расходов"
            filterHint={debouncedSearch ? 'поиск' : null}
          />

          <MobileList>
            {sorted.map((e) => {
              const property = propertyMap[e.property_id];
              return (
                <MobileListItem
                  key={e.id}
                  trailing={
                    canWrite ? (
                      <ActionMenu
                        items={[
                          {
                            label: 'Удалить',
                            icon: <Trash2 className="h-4 w-4" />,
                            danger: true,
                            onClick: () => setDeleting(e),
                          },
                        ]}
                      />
                    ) : undefined
                  }
                >
                  {property ? (
                    <Link to={property.href} className="block">
                      <p className="text-sm font-medium text-gray-900">{property.label}</p>
                      <p className="mt-0.5 text-xs text-gray-500">
                        {EXPENSE_CATEGORY_LABELS[e.category] || e.category} ·{' '}
                        {formatDate(e.date_incurred)}
                      </p>
                      {e.note ? (
                        <p className="mt-0.5 text-xs text-gray-400 truncate">{e.note}</p>
                      ) : null}
                      <p className="mt-1 text-sm font-semibold text-gray-900">
                        {Number(e.amount).toLocaleString('ru-RU')} {e.currency}
                      </p>
                    </Link>
                  ) : (
                    <div>
                      <p className="text-sm font-medium">{e.property_id}</p>
                      <p className="mt-1 text-sm font-semibold">
                        {Number(e.amount).toLocaleString('ru-RU')} {e.currency}
                      </p>
                    </div>
                  )}
                </MobileListItem>
              );
            })}
          </MobileList>

          <div className="hidden sm:block overflow-hidden rounded-xl border border-gray-100 bg-white">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
                    <th className="py-3 px-4 text-left font-medium">Объект</th>
                    <th className="py-3 px-4 text-left font-medium">Категория</th>
                    <th
                      className="py-3 px-4 text-left font-medium cursor-pointer select-none"
                      onClick={() => toggle('amount')}
                    >
                      Сумма {sortKey === 'amount' ? (sortDir === 'asc' ? '▲' : '▼') : ''}
                    </th>
                    <th
                      className="py-3 px-4 text-left font-medium cursor-pointer select-none"
                      onClick={() => toggle('date_incurred')}
                    >
                      Дата {sortKey === 'date_incurred' ? (sortDir === 'asc' ? '▲' : '▼') : ''}
                    </th>
                    <th className="py-3 px-4 text-left font-medium hidden lg:table-cell">
                      Заметка
                    </th>
                    <th className="py-3 px-4 text-right font-medium w-10"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  <AnimatePresence>
                    {sorted.map((e) => {
                      const property = propertyMap[e.property_id];
                      return (
                        <motion.tr
                          key={e.id}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                          className="hover:bg-gray-50 transition-colors"
                        >
                          <td className="py-3 px-4 text-sm text-gray-700">
                            {property ? (
                              <Link to={property.href} className="hover:text-blue-600">
                                {property.label}
                              </Link>
                            ) : (
                              e.property_id
                            )}
                          </td>
                          <td className="py-3 px-4 text-sm text-gray-700">
                            {EXPENSE_CATEGORY_LABELS[e.category] || e.category}
                          </td>
                          <td className="py-3 px-4 text-sm font-medium text-gray-900">
                            {Number(e.amount).toLocaleString('ru-RU')} {e.currency}
                          </td>
                          <td className="py-3 px-4 text-sm text-gray-700">
                            {formatDate(e.date_incurred)}
                          </td>
                          <td className="py-3 px-4 text-sm text-gray-500 hidden lg:table-cell max-w-[200px] truncate">
                            {e.note || '—'}
                          </td>
                          <td className="py-3 px-4 text-right">
                            {canWrite && (
                              <ActionMenu
                                items={[
                                  {
                                    label: 'Удалить',
                                    icon: <Trash2 className="h-4 w-4" />,
                                    danger: true,
                                    onClick: () => setDeleting(e),
                                  },
                                ]}
                              />
                            )}
                          </td>
                        </motion.tr>
                      );
                    })}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
      {canWrite && <ExpenseModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />}
      <ConfirmDialog
        isOpen={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
        title="Удалить расход?"
        message={`Удалить расход на ${deleting ? Number(deleting.amount).toLocaleString('ru-RU') : ''} ${deleting?.currency || ''}?`}
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
}
