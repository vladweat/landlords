import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Pencil, Trash2, Search, Users } from 'lucide-react';
import { showError, showSuccess } from '@/shared/lib/toast';
import { scrollToTop } from '@/shared/lib/scrollToTop';
import { tenantsApi } from '@/features/tenants/api';
import type { Tenant } from '@/entities/tenant';
import { Button } from '@/shared/ui/Button';
import { EmptyState } from '@/shared/ui/EmptyState';
import { ActionMenu } from '@/shared/ui/ActionMenu';
import { ListPagination } from '@/shared/ui/ListPagination';
import { ListErrorState } from '@/shared/ui/ListErrorState';
import { ListSummary } from '@/shared/ui/ListSummary';
import { MobileList, MobileListItem } from '@/shared/ui/MobileList';
import { TenantModal } from '@/features/tenants/components/TenantModal';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { useHotkeys } from '@/shared/hooks/useHotkeys';
import { useCan } from '@/features/auth/permissions';
import { TableSkeleton } from '@/shared/ui/Skeleton';
import { CreditScoreBadge } from '@/features/tenants/components/CreditScoreBadge';
import type { CreditScore } from '@/features/tenants/types';

const PER_PAGE = 20;

interface TenantWithScore extends Tenant {
  score?: { score: CreditScore };
}

export default function TenantsPage() {
  const queryClient = useQueryClient();
  const canWrite = useCan('write_tenants');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState<Tenant | null>(null);
  const [deleting, setDeleting] = useState<Tenant | null>(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebounce(search, 300);

  const openCreate = () => {
    setEditing(null);
    setIsModalOpen(true);
  };
  const openEdit = (t: Tenant) => {
    setEditing(t);
    setIsModalOpen(true);
  };

  useHotkeys(canWrite ? { n: openCreate } : {});

  const { data: paginated, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: ['tenants', page, debouncedSearch],
    queryFn: () =>
      tenantsApi.getAll({
        page,
        per_page: PER_PAGE,
        search: debouncedSearch || undefined,
        include_score: true,
      }),
  });

  const tenants = (paginated?.items || []) as TenantWithScore[];
  const total = paginated?.total ?? 0;
  const pages = paginated?.pages ?? 1;
  const hasActiveFilters = !!debouncedSearch;

  const deleteMutation = useMutation({
    mutationFn: tenantsApi.delete,
    onSuccess: () => {
      scrollToTop();
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      setDeleting(null);
      showSuccess('Арендатор удалён');
    },
    onError: (error) => showError(error, 'Ошибка удаления'),
  });

  const menuItems = (t: Tenant) =>
    canWrite
      ? [
          {
            label: 'Редактировать',
            icon: <Pencil className="h-4 w-4" />,
            onClick: () => openEdit(t),
          },
          {
            label: 'Удалить',
            icon: <Trash2 className="h-4 w-4" />,
            danger: true,
            onClick: () => setDeleting(t),
          },
        ]
      : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Арендаторы</h1>
          <p className="mt-1 text-sm text-gray-500">Контакты и рейтинг платёжной дисциплины</p>
        </div>
        {canWrite && (
          <Button onClick={openCreate} leftIcon={<Plus className="h-4 w-4" />}>
            Добавить
          </Button>
        )}
      </div>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          aria-label="Поиск по имени или email"
          placeholder="Поиск по имени или email..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {isLoading ? (
        <TableSkeleton rows={5} cols={5} />
      ) : isError ? (
        <ListErrorState onRetry={() => void refetch()} isRetrying={isFetching} />
      ) : tenants.length === 0 ? (
        <EmptyState
          icon={Users}
          title={hasActiveFilters ? 'Ничего не найдено' : 'Нет арендаторов'}
          description={
            hasActiveFilters
              ? 'Измените параметры поиска'
              : 'Добавьте арендатора, чтобы создавать контракты'
          }
          action={
            !hasActiveFilters && canWrite
              ? { label: 'Добавить арендатора', onClick: openCreate }
              : undefined
          }
        />
      ) : (
        <>
          <ListSummary
            total={total}
            entityLabel="арендаторов"
            filterHint={hasActiveFilters ? 'поиск' : null}
          />

          <MobileList>
            {tenants.map((t) => (
              <MobileListItem
                key={t.id}
                onClick={canWrite ? () => openEdit(t) : undefined}
                trailing={menuItems(t).length > 0 ? <ActionMenu items={menuItems(t)} /> : undefined}
              >
                <p className="text-sm font-medium text-gray-900">{t.full_name}</p>
                <p className="mt-0.5 text-xs text-gray-500">
                  {[t.email, t.phone].filter(Boolean).join(' · ') || 'Нет контактов'}
                </p>
                <div className="mt-1.5">
                  <CreditScoreBadge score={t.score?.score} />
                </div>
              </MobileListItem>
            ))}
          </MobileList>

          <div className="hidden sm:block overflow-hidden rounded-xl border border-gray-100 bg-white">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
                  <th className="py-3 px-4 text-left font-medium">Имя</th>
                  <th className="py-3 px-4 text-left font-medium">Email</th>
                  <th className="py-3 px-4 text-left font-medium">Телефон</th>
                  <th className="py-3 px-4 text-left font-medium">Рейтинг</th>
                  <th className="py-3 px-4 text-right font-medium w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <AnimatePresence>
                  {tenants.map((t) => (
                    <motion.tr
                      key={t.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="hover:bg-gray-50 transition-colors"
                    >
                      <td className="py-3 px-4 text-sm font-medium">
                        {canWrite ? (
                          <button
                            type="button"
                            onClick={() => openEdit(t)}
                            className="hover:text-blue-600 text-left"
                          >
                            {t.full_name}
                          </button>
                        ) : (
                          t.full_name
                        )}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-700">{t.email}</td>
                      <td className="py-3 px-4 text-sm text-gray-700">{t.phone}</td>
                      <td className="py-3 px-4">
                        <CreditScoreBadge score={t.score?.score} />
                      </td>
                      <td className="py-3 px-4 text-right">
                        {canWrite && <ActionMenu items={menuItems(t)} />}
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>

          <ListPagination
            page={page}
            pages={pages}
            total={total}
            onPageChange={(p) => {
              setPage(p);
              scrollToTop();
            }}
            entityLabel="арендаторов"
          />
        </>
      )}
      <TenantModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditing(null);
        }}
        tenant={editing}
      />
      <ConfirmDialog
        isOpen={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
        title="Удалить арендатора?"
        message={`Удалить "${deleting?.full_name}"?`}
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
}
