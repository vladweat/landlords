import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Pencil, Trash2, Search, Building2, Download } from 'lucide-react';
import { toast } from 'sonner';
import { showError } from '@/shared/lib/toast';
import { scrollToTop } from '@/shared/lib/scrollToTop';
import { propertiesApi } from '@/features/properties/api';
import { contractsApi } from '@/features/contracts/api';
import { accountApi } from '@/features/account/api';
import type { Property } from '@/entities/property';
import { Button } from '@/shared/ui/Button';
import { EmptyState } from '@/shared/ui/EmptyState';
import { ActionMenu } from '@/shared/ui/ActionMenu';
import { ListPagination } from '@/shared/ui/ListPagination';
import { ListErrorState } from '@/shared/ui/ListErrorState';
import { ListSummary } from '@/shared/ui/ListSummary';
import { MobileList, MobileListItem } from '@/shared/ui/MobileList';
import { PropertyModal } from './PropertyModal';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { useHotkeys } from '@/shared/hooks/useHotkeys';
import { useCan } from '@/features/auth/permissions';
import { TableSkeleton } from '@/shared/ui/Skeleton';
import { exportCSV } from '@/shared/lib/exportCSV';
import { ROIBadge } from '@/features/properties/components/ROIBadge';
import { PROPERTY_TYPE_LABELS } from '@/entities/property';

const PER_PAGE = 20;

const TYPE_OPTIONS = [
  { value: 'all', label: 'Все типы' },
  { value: 'apartment', label: 'Квартира' },
  { value: 'house', label: 'Дом' },
  { value: 'room', label: 'Комната' },
  { value: 'commercial', label: 'Коммерция' },
] as const;

export default function PropertiesPage() {
  const queryClient = useQueryClient();
  const canWrite = useCan('write_properties');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState<Property | null>(null);
  const [deleting, setDeleting] = useState<Property | null>(null);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebounce(search, 300);

  const { data: subscription } = useQuery({
    queryKey: ['account-subscription'],
    queryFn: accountApi.getSubscription,
  });
  const propertiesAtLimit =
    !!subscription &&
    subscription.usage.properties >= subscription.limits.max_properties;

  const openCreate = () => {
    if (propertiesAtLimit) {
      toast.error('Достигнут лимит объектов тарифа. Смените тариф в Настройках.');
      return;
    }
    setEditing(null);
    setIsModalOpen(true);
  };
  useHotkeys(canWrite ? { n: openCreate } : {});

  const { data: paginated, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: ['properties', page, debouncedSearch, typeFilter],
    queryFn: () =>
      propertiesApi.getAll({
        page,
        per_page: PER_PAGE,
        search: debouncedSearch || undefined,
        type: typeFilter !== 'all' ? typeFilter : undefined,
        sort_by: 'address',
        sort_dir: 'asc',
      }),
  });
  const { data: contractsData } = useQuery({
    queryKey: ['contracts'],
    queryFn: () => contractsApi.getAll({ per_page: 100 }),
    staleTime: 10 * 60 * 1000,
  });

  const properties = paginated?.items || [];
  const total = paginated?.total ?? 0;
  const pages = paginated?.pages ?? 1;
  const contracts = contractsData?.items || [];

  const contractByProperty = useMemo(() => {
    const map: Record<string, { id: string; status: string; end_date: string }> = {};
    contracts.forEach((c) => {
      if (c.status === 'active' || c.status === 'overdue') {
        map[c.property_id] = { id: c.id, status: c.status, end_date: c.end_date };
      }
    });
    return map;
  }, [contracts]);

  const filterHint = useMemo(() => {
    const parts: string[] = [];
    if (debouncedSearch) parts.push('поиск');
    if (typeFilter !== 'all') {
      parts.push((PROPERTY_TYPE_LABELS as Record<string, string>)[typeFilter] ?? typeFilter);
    }
    return parts.length ? parts.join(' + ') : null;
  }, [debouncedSearch, typeFilter]);

  const hasActiveFilters = !!debouncedSearch || typeFilter !== 'all';

  const deleteMutation = useMutation({
    mutationFn: propertiesApi.delete,
    onSuccess: () => {
      scrollToTop();
      queryClient.invalidateQueries({ queryKey: ['properties'] });
      queryClient.invalidateQueries({ queryKey: ['account-subscription'] });
      setDeleting(null);
      toast.success('Объект удалён');
    },
    onError: (error) => showError(error, 'Ошибка удаления'),
  });

  const menuItems = (p: Property) =>
    canWrite
      ? [
          {
            label: 'Редактировать',
            icon: <Pencil className="h-4 w-4" />,
            onClick: () => {
              setEditing(p);
              setIsModalOpen(true);
            },
          },
          {
            label: 'Удалить',
            icon: <Trash2 className="h-4 w-4" />,
            danger: true,
            onClick: () => setDeleting(p),
          },
        ]
      : [];

  const statusNode = (propertyId: string) => {
    const contract = contractByProperty[propertyId];
    if (contract) {
      return (
        <Link
          to={`/contracts/${contract.id}`}
          className="inline-flex items-center gap-2 text-sm text-gray-700 hover:text-blue-600"
        >
          <span
            className={`w-2 h-2 rounded-full ${contract.status === 'active' ? 'bg-emerald-500' : 'bg-red-500'}`}
          />
          {contract.status === 'active' ? 'Сдаётся' : 'Просрочка'}
        </Link>
      );
    }
    return (
      <span className="inline-flex items-center gap-2 text-sm text-gray-500">
        <span className="w-2 h-2 rounded-full bg-gray-300" />
        Свободен
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Объекты</h1>
          <p className="mt-1 text-sm text-gray-500">Адреса, занятость и доходность</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() =>
              exportCSV(properties, 'objects', ['Адрес', 'Тип', 'Площадь'], [
                'address',
                'type',
                'size_m2',
              ])
            }
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
            title="Экспорт текущей страницы в CSV"
          >
            <Download className="h-4 w-4" />
            <span className="hidden sm:inline">CSV</span>
          </button>
          {canWrite && (
            <Button
              onClick={openCreate}
              leftIcon={<Plus className="h-4 w-4" />}
              disabled={propertiesAtLimit}
              title={propertiesAtLimit ? 'Достигнут лимит тарифа' : undefined}
            >
              Добавить
            </Button>
          )}
        </div>
      </div>
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            placeholder="Поиск по адресу..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
          aria-label="Фильтр по типу"
        >
          {TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <TableSkeleton rows={5} cols={5} />
      ) : isError ? (
        <ListErrorState onRetry={() => void refetch()} isRetrying={isFetching} />
      ) : properties.length === 0 ? (
        <EmptyState
          icon={Building2}
          title={hasActiveFilters ? 'Ничего не найдено' : 'Нет объектов'}
          description={
            hasActiveFilters ? 'Измените параметры поиска' : 'Добавьте первый объект'
          }
          action={
            !hasActiveFilters && canWrite && !propertiesAtLimit
              ? { label: 'Добавить объект', onClick: openCreate }
              : undefined
          }
        />
      ) : (
        <>
          <ListSummary total={total} entityLabel="объектов" filterHint={filterHint} />

          <MobileList>
            {properties.map((p) => (
              <MobileListItem
                key={p.id}
                trailing={menuItems(p).length > 0 ? <ActionMenu items={menuItems(p)} /> : undefined}
              >
                <Link to={`/properties/${p.id}`} className="block">
                  <p className="text-sm font-medium text-gray-900">{p.address}</p>
                  <p className="mt-0.5 text-xs text-gray-500">
                    {PROPERTY_TYPE_LABELS[p.type] ?? p.type} · {p.size_m2} м²
                  </p>
                  <div className="mt-1.5 flex items-center gap-3">{statusNode(p.id)}</div>
                </Link>
              </MobileListItem>
            ))}
          </MobileList>

          <div className="hidden sm:block overflow-hidden rounded-xl border border-gray-100 bg-white">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
                  <th className="py-3 px-4 text-left font-medium">Адрес</th>
                  <th className="py-3 px-4 text-left font-medium">Статус</th>
                  <th className="py-3 px-4 text-left font-medium">Тип</th>
                  <th className="py-3 px-4 text-left font-medium">Площадь</th>
                  <th className="py-3 px-4 text-left font-medium hidden lg:table-cell">
                    Доходность
                  </th>
                  <th className="py-3 px-4 text-right font-medium w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <AnimatePresence>
                  {properties.map((p) => (
                    <motion.tr
                      key={p.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="hover:bg-gray-50 transition-colors"
                    >
                      <td className="py-3 px-4 text-sm font-medium">
                        <Link to={`/properties/${p.id}`} className="hover:text-blue-600">
                          {p.address}
                        </Link>
                      </td>
                      <td className="py-3 px-4">{statusNode(p.id)}</td>
                      <td className="py-3 px-4 text-sm text-gray-700">
                        {PROPERTY_TYPE_LABELS[p.type] ?? p.type}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-700">{p.size_m2} м²</td>
                      <td className="py-3 px-4 hidden lg:table-cell">
                        <ROIBadge roi={p.roi?.roi ?? null} />
                      </td>
                      <td className="py-3 px-4 text-right">
                        {canWrite && <ActionMenu items={menuItems(p)} />}
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
            entityLabel="объектов"
          />
        </>
      )}
      <PropertyModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditing(null);
        }}
        property={editing}
      />
      <ConfirmDialog
        isOpen={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
        title="Удалить объект?"
        message={`Удалить "${deleting?.address}"?`}
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
}
