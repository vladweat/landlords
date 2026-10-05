import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Trash2, CreditCard, Search } from 'lucide-react';
import { toast } from 'sonner';
import { showError } from '@/shared/lib/toast';
import { formatDate } from '@/shared/lib/utils';
import { scrollToTop } from '@/shared/lib/scrollToTop';
import { paymentsApi } from '@/features/payments/api';
import { contractsApi } from '@/features/contracts/api';
import { propertiesApi } from '@/features/properties/api';
import { tenantsApi } from '@/features/tenants/api';
import type { Payment } from '@/entities/payment';
import { Button } from '@/shared/ui/Button';
import { EmptyState } from '@/shared/ui/EmptyState';
import { ActionMenu } from '@/shared/ui/ActionMenu';
import { ListErrorState } from '@/shared/ui/ListErrorState';
import { ListSummary } from '@/shared/ui/ListSummary';
import { MobileList, MobileListItem } from '@/shared/ui/MobileList';
import { PaymentModal } from './PaymentModal';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { useHotkeys } from '@/shared/hooks/useHotkeys';
import { useSort } from '@/shared/hooks/useSort';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { useCan } from '@/features/auth/permissions';
import { TableSkeleton } from '@/shared/ui/Skeleton';
import { shortAddress } from '@/shared/lib/address';

const methodLabels: Record<string, string> = {
  transfer: 'Перевод',
  cash: 'Наличные',
  card: 'Карта',
};

export default function PaymentsPage() {
  const queryClient = useQueryClient();
  const canWrite = useCan('write_payments');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [deleting, setDeleting] = useState<Payment | null>(null);
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search, 300);
  useHotkeys(canWrite ? { n: () => setIsModalOpen(true) } : {});

  const { data: payments, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: ['payments'],
    queryFn: paymentsApi.getAll,
  });
  const { data: contractsData } = useQuery({
    queryKey: ['contracts'],
    queryFn: () => contractsApi.getAll({ per_page: 100 }),
    staleTime: 10 * 60 * 1000,
  });
  const { data: propertiesData } = useQuery({
    queryKey: ['properties'],
    queryFn: () => propertiesApi.getAll({ per_page: 100 }),
    staleTime: 10 * 60 * 1000,
  });
  const { data: tenantsData } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantsApi.getAll({ per_page: 100 }),
    staleTime: 10 * 60 * 1000,
  });

  const contracts = contractsData?.items || [];
  const properties = propertiesData?.items || [];
  const tenants = tenantsData?.items || [];

  const contractMap = useMemo(() => {
    const m: Record<string, { label: string; href: string }> = {};
    contracts.forEach((c) => {
      const p = properties.find((x) => x.id === c.property_id);
      const t = tenants.find((x) => x.id === c.tenant_id);
      m[c.id] = {
        label: `${shortAddress(p?.address || '—')} / ${t?.full_name || '—'}`,
        href: `/contracts/${c.id}`,
      };
    });
    return m;
  }, [contracts, properties, tenants]);

  const filtered = useMemo(() => {
    if (!payments) return [];
    if (!debouncedSearch) return payments;
    const q = debouncedSearch.toLowerCase();
    return payments.filter((p) => {
      const label = (contractMap[p.contract_id]?.label || '').toLowerCase();
      const method = (methodLabels[p.method] || p.method).toLowerCase();
      return label.includes(q) || method.includes(q) || String(p.amount).includes(q);
    });
  }, [payments, debouncedSearch, contractMap]);

  const { sorted, sortKey, sortDir, toggle } = useSort(filtered);
  const hasSource = (payments?.length ?? 0) > 0;
  const emptyAfterFilter = hasSource && filtered.length === 0;

  const deleteMutation = useMutation({
    mutationFn: paymentsApi.delete,
    onSuccess: () => {
      scrollToTop();
      queryClient.invalidateQueries({ queryKey: ['payments'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-last-payments'] });
      setDeleting(null);
      toast.success('Платёж удалён');
    },
    onError: (error) => showError(error, 'Ошибка удаления'),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Платежи</h1>
          <p className="mt-1 text-sm text-gray-500">Поступления по договорам</p>
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
          placeholder="Поиск по договору, сумме, способу..."
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
          icon={CreditCard}
          title="Нет платежей"
          description="Платежи появятся после создания договоров и начислений"
          action={
            canWrite
              ? { label: 'Добавить платёж', onClick: () => setIsModalOpen(true) }
              : undefined
          }
        />
      ) : emptyAfterFilter ? (
        <EmptyState
          icon={CreditCard}
          title="Ничего не найдено"
          description="Измените параметры поиска"
        />
      ) : (
        <>
          <ListSummary
            total={filtered.length}
            entityLabel="платежей"
            filterHint={debouncedSearch ? 'поиск' : null}
          />

          <MobileList>
            {sorted.map((p) => {
              const contract = contractMap[p.contract_id];
              return (
                <MobileListItem
                  key={p.id}
                  trailing={
                    canWrite ? (
                      <ActionMenu
                        items={[
                          {
                            label: 'Удалить',
                            icon: <Trash2 className="h-4 w-4" />,
                            danger: true,
                            onClick: () => setDeleting(p),
                          },
                        ]}
                      />
                    ) : undefined
                  }
                >
                  {contract ? (
                    <Link to={contract.href} className="block">
                      <p className="text-sm font-medium text-gray-900">{contract.label}</p>
                      <p className="mt-0.5 text-xs text-gray-500">
                        {methodLabels[p.method] || p.method} · {formatDate(p.date_paid)}
                      </p>
                      <p className="mt-1 text-sm font-semibold text-gray-900">
                        {Number(p.amount).toLocaleString('ru-RU')} {p.currency}
                      </p>
                    </Link>
                  ) : (
                    <div>
                      <p className="text-sm font-medium text-gray-900">{p.contract_id}</p>
                      <p className="mt-1 text-sm font-semibold">
                        {Number(p.amount).toLocaleString('ru-RU')} {p.currency}
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
                    <th className="py-3 px-4 text-left font-medium">Договор</th>
                    <th
                      className="py-3 px-4 text-left font-medium cursor-pointer select-none"
                      onClick={() => toggle('amount')}
                    >
                      Сумма {sortKey === 'amount' ? (sortDir === 'asc' ? '▲' : '▼') : ''}
                    </th>
                    <th className="py-3 px-4 text-left font-medium">Способ</th>
                    <th
                      className="py-3 px-4 text-left font-medium cursor-pointer select-none"
                      onClick={() => toggle('date_paid')}
                    >
                      Дата {sortKey === 'date_paid' ? (sortDir === 'asc' ? '▲' : '▼') : ''}
                    </th>
                    <th className="py-3 px-4 text-right font-medium w-10"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  <AnimatePresence>
                    {sorted.map((p) => {
                      const contract = contractMap[p.contract_id];
                      return (
                        <motion.tr
                          key={p.id}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                          className="hover:bg-gray-50 transition-colors"
                        >
                          <td className="py-3 px-4 text-sm text-gray-700">
                            {contract ? (
                              <Link to={contract.href} className="hover:text-blue-600">
                                {contract.label}
                              </Link>
                            ) : (
                              p.contract_id
                            )}
                          </td>
                          <td className="py-3 px-4 text-sm font-medium text-gray-900">
                            {Number(p.amount).toLocaleString('ru-RU')} {p.currency}
                          </td>
                          <td className="py-3 px-4 text-sm text-gray-700">
                            {methodLabels[p.method] || p.method}
                          </td>
                          <td className="py-3 px-4 text-sm text-gray-700">
                            {formatDate(p.date_paid)}
                          </td>
                          <td className="py-3 px-4 text-right">
                            {canWrite && (
                              <ActionMenu
                                items={[
                                  {
                                    label: 'Удалить',
                                    icon: <Trash2 className="h-4 w-4" />,
                                    danger: true,
                                    onClick: () => setDeleting(p),
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
      {canWrite && <PaymentModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />}
      <ConfirmDialog
        isOpen={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
        title="Удалить платёж?"
        message={`Удалить платёж на ${deleting ? Number(deleting.amount).toLocaleString('ru-RU') : ''} ${deleting?.currency || ''}?`}
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
}
