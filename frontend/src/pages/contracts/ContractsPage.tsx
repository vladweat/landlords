import { useState, useMemo, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  Pencil,
  Trash2,
  Play,
  Check,
  XCircle,
  Filter,
  FileText,
  Search,
  RefreshCw,
  CalendarPlus,
  FileSpreadsheet,
  X,
} from 'lucide-react';
import { toast } from 'sonner';
import { showError } from '@/shared/lib/toast';
import { scrollToTop } from '@/shared/lib/scrollToTop';
import { contractsApi } from '@/features/contracts/api';
import { propertiesApi } from '@/features/properties/api';
import { tenantsApi } from '@/features/tenants/api';
import { reportsApi, type ReportFormat } from '@/features/reports/api';
import type { Contract } from '@/entities/contract';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { EmptyState } from '@/shared/ui/EmptyState';
import { ActionMenu } from '@/shared/ui/ActionMenu';
import { ListPagination } from '@/shared/ui/ListPagination';
import { ListErrorState } from '@/shared/ui/ListErrorState';
import { ListSummary } from '@/shared/ui/ListSummary';
import { MobileList, MobileListItem } from '@/shared/ui/MobileList';
import { ContractModal } from './ContractModal';
import { TerminateContractWizard } from '@/features/contracts/components/TerminateContractWizard';
import { RenewContractWizard } from '@/features/contracts/components/RenewContractWizard';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { useHotkeys } from '@/shared/hooks/useHotkeys';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { useEscapeKey } from '@/shared/hooks/useEscapeKey';
import { useCan } from '@/features/auth/permissions';
import { TableSkeleton } from '@/shared/ui/Skeleton';
import { shortAddress } from '@/shared/lib/address';

const statusConfig: Record<string, { label: string; color: string }> = {
  draft: { label: 'Черновик', color: 'bg-gray-400' },
  active: { label: 'Активен', color: 'bg-emerald-500' },
  ended: { label: 'Завершён', color: 'bg-blue-500' },
  overdue: { label: 'Просрочен', color: 'bg-red-500' },
  terminated: { label: 'Расторгнут', color: 'bg-amber-500' },
};
const PER_PAGE = 20;

function defaultStart(): string {
  const d = new Date();
  return `${d.getFullYear()}-01-01`;
}

function defaultEnd(): string {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${m}-${day}`;
}

function BulkExportDialog({
  isOpen,
  onClose,
  contractIds,
}: {
  isOpen: boolean;
  onClose: () => void;
  contractIds: string[];
}) {
  useEscapeKey(onClose);
  const [startDate, setStartDate] = useState(defaultStart);
  const [endDate, setEndDate] = useState(defaultEnd);
  const [loading, setLoading] = useState<ReportFormat | null>(null);
  const invalid = !startDate || !endDate || endDate < startDate;

  const handleExport = async (format: ReportFormat) => {
    if (invalid) {
      toast.error('Проверьте период: дата окончания не раньше начала');
      return;
    }
    setLoading(format);
    try {
      await reportsApi.export({
        start_date: startDate,
        end_date: endDate,
        format,
        contract_ids: contractIds,
      });
      toast.success(format === 'xlsx' ? 'XLSX скачан' : 'CSV скачан');
      onClose();
    } catch (error) {
      showError(error, 'Ошибка экспорта');
    } finally {
      setLoading(null);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/50"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">
                  Экспорт ({contractIds.length})
                </h2>
                <button type="button" onClick={onClose} className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <p className="mb-4 text-sm text-gray-500">
                Платежи, начисления и расходы по выбранным договорам за период
              </p>
              <div className="mb-4 grid gap-4 sm:grid-cols-2">
                <Input label="С" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                <Input label="По" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </div>
              {invalid && (
                <p className="mb-3 text-sm text-red-600">Дата окончания не может быть раньше даты начала</p>
              )}
              <div className="flex flex-wrap gap-3">
                <Button
                  onClick={() => void handleExport('xlsx')}
                  disabled={invalid}
                  isLoading={loading === 'xlsx'}
                  leftIcon={<FileSpreadsheet className="h-4 w-4" />}
                >
                  XLSX
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => void handleExport('csv')}
                  disabled={invalid}
                  isLoading={loading === 'csv'}
                  leftIcon={<FileText className="h-4 w-4" />}
                >
                  CSV
                </Button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

type MenuItem = {
  label: string;
  icon: ReactNode;
  onClick: () => void;
  danger?: boolean;
};

const STATUS_FILTERS = [
  { value: 'all', label: 'Все' },
  { value: 'draft', label: 'Черновики' },
  { value: 'active', label: 'Активные' },
  { value: 'overdue', label: 'Просрочены' },
  { value: 'ended', label: 'Завершены' },
  { value: 'terminated', label: 'Расторгнуты' },
] as const;

export default function ContractsPage() {
  const queryClient = useQueryClient();
  const canWrite = useCan('write_contracts');
  const canWriteCharges = useCan('write_charges');
  const [searchParams, setSearchParams] = useSearchParams();
  const statusFilter = searchParams.get('status') || 'all';
  const setStatusFilter = (s: string) => setSearchParams(s === 'all' ? {} : { status: s });
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState<Contract | null>(null);
  const [deleting, setDeleting] = useState<Contract | null>(null);
  const [terminating, setTerminating] = useState<Contract | null>(null);
  const [renewing, setRenewing] = useState<Contract | null>(null);
  const [changingStatus, setChangingStatus] = useState<string | null>(null);
  const [statusConfirm, setStatusConfirm] = useState<{id:string;status:Contract['status'];label:string}|null>(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkGenerateOpen, setBulkGenerateOpen] = useState(false);
  const [bulkExportOpen, setBulkExportOpen] = useState(false);
  const debouncedSearch = useDebounce(search, 300);
  useHotkeys(canWrite ? { n: () => { setEditing(null); setIsModalOpen(true); } } : {});

  const { data: paginated, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: ['contracts', page, statusFilter, debouncedSearch],
    queryFn: () => contractsApi.getAll({ page, per_page: PER_PAGE, status: statusFilter !== 'all' ? statusFilter : undefined, search: debouncedSearch || undefined }),
  });
  const { data: propertiesData } = useQuery({ queryKey: ['properties'], queryFn: () => propertiesApi.getAll({ per_page: 100 }), staleTime: 10*60*1000 });
  const { data: tenantsData } = useQuery({ queryKey: ['tenants'], queryFn: () => tenantsApi.getAll({ per_page: 100 }), staleTime: 10*60*1000 });

  const contracts = paginated?.items || [];
  const total = paginated?.total ?? 0;
  const pages = paginated?.pages ?? 1;
  const properties = propertiesData?.items || [];
  const tenants = tenantsData?.items || [];

  const pMap = useMemo(() => { const m: Record<string, string> = {}; properties.forEach((p) => m[p.id] = p.address); return m; }, [properties]);
  const tMap = useMemo(() => { const m: Record<string, string> = {}; tenants.forEach((t) => m[t.id] = t.full_name); return m; }, [tenants]);

  const pageIds = useMemo(() => contracts.map((c) => c.id), [contracts]);
  const allPageSelected = pageIds.length > 0 && pageIds.every((id) => selected.has(id));
  const selectedIds = useMemo(() => Array.from(selected), [selected]);
  const selectedOnOtherPages = [...selected].some((id) => !pageIds.includes(id));

  const filterHint = useMemo(() => {
    const parts: string[] = [];
    if (debouncedSearch) parts.push('поиск');
    if (statusFilter !== 'all') {
      parts.push(STATUS_FILTERS.find((f) => f.value === statusFilter)?.label.toLowerCase() || statusFilter);
    }
    return parts.length ? parts.join(' + ') : null;
  }, [debouncedSearch, statusFilter]);

  const toggleOne = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAllPage = () => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (allPageSelected) {
        pageIds.forEach((id) => next.delete(id));
      } else {
        pageIds.forEach((id) => next.add(id));
      }
      return next;
    });
  };

  const clearSelection = () => setSelected(new Set());

  const deleteMutation = useMutation({
    mutationFn: contractsApi.delete,
    onSuccess: () => { scrollToTop(); queryClient.invalidateQueries({ queryKey: ['contracts'] }); setDeleting(null); toast.success('Договор удалён'); },
    onError: (error) => showError(error, 'Ошибка удаления'),
  });
  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: Contract['status'] }) => contractsApi.update(id, { status }),
    onMutate: ({ id }) => setChangingStatus(id), onSettled: () => setChangingStatus(null),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['contracts'] }); },
    onError: (error) => showError(error, 'Ошибка смены статуса'),
  });

  const bulkGenerateMutation = useMutation({
    mutationFn: () => contractsApi.generateChargesBulk(selectedIds),
    onSuccess: (data) => {
      setBulkGenerateOpen(false);
      clearSelection();
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
      const enq = data.enqueued.length;
      const skip = data.skipped.length;
      if (enq > 0 && skip === 0) {
        toast.success(`Генерация запущена для ${enq} договоров`);
      } else if (enq > 0) {
        toast.success(`Запущено: ${enq}, пропущено: ${skip}`);
      } else {
        toast.message(`Ничего не запущено (пропущено: ${skip})`);
      }
    },
    onError: (error) => showError(error, 'Не удалось запустить генерацию'),
  });

  const Spinner = () => <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />;

  const contractMenuItems = (c: Contract): MenuItem[] => {
    if (!canWrite) return [];
    return [
      ...(c.status === 'draft' ? [{ label: 'Активировать', icon: changingStatus === c.id ? <Spinner/> : <Play className="h-4 w-4" />, onClick: () => setStatusConfirm({id:c.id,status:'active' as const,label:'Активировать'}) }] : []),
      ...(c.status === 'active' || c.status === 'overdue' ? [{ label: 'Завершить', icon: changingStatus === c.id ? <Spinner/> : <Check className="h-4 w-4" />, onClick: () => setStatusConfirm({id:c.id,status:'ended' as const,label:'Завершить'}) }] : []),
      ...(c.status === 'active' || c.status === 'overdue' || c.status === 'ended' ? [{ label: 'Продлить', icon: <RefreshCw className="h-4 w-4" />, onClick: () => setRenewing(c) }] : []),
      ...(c.status === 'draft' || c.status === 'active' || c.status === 'overdue' ? [{ label: 'Расторгнуть', icon: <XCircle className="h-4 w-4" />, onClick: () => setTerminating(c) }] : []),
      { label: 'Редактировать', icon: <Pencil className="h-4 w-4" />, onClick: () => { setEditing(c); setIsModalOpen(true); } },
      { label: 'Удалить', icon: <Trash2 className="h-4 w-4" />, danger: true, onClick: () => setDeleting(c) },
    ];
  };

  const hasActiveFilters = statusFilter !== 'all' || !!debouncedSearch;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Договоры</h1>
          <p className="mt-1 text-sm text-gray-500">Статусы, продление и массовые действия</p>
        </div>
        {canWrite && (
          <Button onClick={() => { setEditing(null); setIsModalOpen(true); }} leftIcon={<Plus className="h-4 w-4" />}>Добавить</Button>
        )}
      </div>
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1"><Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input placeholder="Поиск по объекту или арендатору..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); clearSelection(); }} className="w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>
      <div className="flex flex-nowrap items-center gap-2 overflow-x-auto pb-2 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
        <Filter className="h-4 w-4 text-gray-400 flex-shrink-0" />
        {STATUS_FILTERS.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => { setStatusFilter(value); setPage(1); clearSelection(); }}
            className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium whitespace-nowrap ${statusFilter === value ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          >
            {label}
          </button>
        ))}
      </div>

      {selected.size > 0 && (
        <div className="sticky top-0 z-10 flex flex-wrap items-center gap-3 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3">
          <div className="min-w-0">
            <span className="text-sm font-medium text-blue-900">Выбрано: {selected.size}</span>
            {selectedOnOtherPages && (
              <p className="text-xs text-blue-700/80">Включая договоры с других страниц</p>
            )}
          </div>
          {canWriteCharges && (
            <Button size="sm" leftIcon={<CalendarPlus className="h-4 w-4" />} onClick={() => setBulkGenerateOpen(true)}>
              Сгенерировать начисления
            </Button>
          )}
          <Button size="sm" variant="secondary" leftIcon={<FileSpreadsheet className="h-4 w-4" />} onClick={() => setBulkExportOpen(true)}>
            Экспорт
          </Button>
          <Button size="sm" variant="ghost" onClick={clearSelection}>Снять выбор</Button>
        </div>
      )}

      {isLoading ? (
        <TableSkeleton rows={5} cols={6} />
      ) : isError ? (
        <ListErrorState onRetry={() => void refetch()} isRetrying={isFetching} />
      ) : contracts.length === 0 ? (
        <EmptyState
          icon={FileText}
          title={hasActiveFilters ? 'Ничего не найдено' : 'Нет договоров'}
          description={hasActiveFilters ? 'Измените параметры поиска или фильтра' : 'Создайте договор, чтобы начать учёт начислений и платежей'}
          action={!hasActiveFilters && canWrite ? { label: 'Создать договор', onClick: () => { setEditing(null); setIsModalOpen(true); } } : undefined}
        />
      ) : (
        <>
          <ListSummary total={total} entityLabel="договоров" filterHint={filterHint} />

          <MobileList>
            {contracts.map((c) => {
              const address = shortAddress(pMap[c.property_id] || c.property_id);
              const tenant = tMap[c.tenant_id] || c.tenant_id;
              const menu = contractMenuItems(c);
              return (
                <MobileListItem
                  key={c.id}
                  className={selected.has(c.id) ? 'border-blue-200 bg-blue-50/40' : undefined}
                  leading={
                    <input
                      type="checkbox"
                      checked={selected.has(c.id)}
                      onChange={() => toggleOne(c.id)}
                      aria-label={`Выбрать договор ${address}`}
                      className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  }
                  trailing={menu.length > 0 ? <ActionMenu items={menu} /> : undefined}
                >
                  <Link to={`/contracts/${c.id}`} className="block">
                    <p className="text-sm font-medium text-gray-900">{address}</p>
                    <p className="mt-0.5 text-xs text-gray-500">{tenant}</p>
                    <div className="mt-1.5 flex items-center gap-2 text-xs text-gray-600">
                      <span className={`h-2 w-2 rounded-full ${statusConfig[c.status]?.color || 'bg-gray-400'}`} />
                      <span>{statusConfig[c.status]?.label || c.status}</span>
                      <span className="text-gray-300">·</span>
                      <span>{Number(c.rent_amount).toLocaleString('ru-RU')} {c.currency}</span>
                    </div>
                  </Link>
                </MobileListItem>
              );
            })}
          </MobileList>

          <div className="hidden sm:block overflow-hidden rounded-xl border border-gray-100 bg-white">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
                    <th className="py-3 px-4 w-10">
                      <input
                        type="checkbox"
                        checked={allPageSelected}
                        onChange={toggleAllPage}
                        aria-label="Выбрать все на странице"
                        className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                    </th>
                    <th className="py-3 px-4 text-left font-medium">Объект</th>
                    <th className="py-3 px-4 text-left font-medium">Арендатор</th>
                    <th className="py-3 px-4 text-left font-medium">Сумма</th>
                    <th className="py-3 px-4 text-left font-medium">Статус</th>
                    <th className="py-3 px-4 text-right font-medium w-10"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  <AnimatePresence>
                    {contracts.map((c) => (
                      <motion.tr
                        key={c.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className={`hover:bg-gray-50 transition-colors ${selected.has(c.id) ? 'bg-blue-50/50' : ''}`}
                      >
                        <td className="py-3 px-4">
                          <input
                            type="checkbox"
                            checked={selected.has(c.id)}
                            onChange={() => toggleOne(c.id)}
                            aria-label={`Выбрать договор ${shortAddress(pMap[c.property_id]||c.property_id)}`}
                            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                        </td>
                        <td className="py-3 px-4 text-sm font-medium">
                          <Link to={`/contracts/${c.id}`} className="hover:text-blue-600">
                            {shortAddress(pMap[c.property_id] || c.property_id)}
                          </Link>
                        </td>
                        <td className="py-3 px-4 text-sm text-gray-700">{tMap[c.tenant_id] || c.tenant_id}</td>
                        <td className="py-3 px-4 text-sm text-gray-700">{Number(c.rent_amount).toLocaleString('ru-RU')} {c.currency}</td>
                        <td className="py-3 px-4">
                          <span className="inline-flex items-center gap-2 text-sm text-gray-700">
                            <span className={`w-2 h-2 rounded-full ${statusConfig[c.status]?.color || 'bg-gray-400'}`} />
                            {statusConfig[c.status]?.label || c.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          {canWrite && <ActionMenu items={contractMenuItems(c)} />}
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          </div>

          <ListPagination
            page={page}
            pages={pages}
            total={total}
            onPageChange={(p) => { setPage(p); scrollToTop(); }}
            entityLabel="договоров"
          />
        </>
      )}
      <ContractModal isOpen={isModalOpen} onClose={()=>{setIsModalOpen(false);setEditing(null)}} contract={editing}/>
      <TerminateContractWizard isOpen={!!terminating} onClose={() => setTerminating(null)} contract={terminating} />
      <RenewContractWizard isOpen={!!renewing} onClose={() => setRenewing(null)} contract={renewing} />
      <ConfirmDialog isOpen={!!deleting} onClose={()=>setDeleting(null)} onConfirm={()=>deleting&&deleteMutation.mutate(deleting.id)} title="Удалить договор?" message="Вы уверены?" isLoading={deleteMutation.isPending}/>
      <ConfirmDialog isOpen={!!statusConfirm} onClose={()=>setStatusConfirm(null)} onConfirm={()=>{if(statusConfirm){statusMutation.mutate({id:statusConfirm.id,status:statusConfirm.status});setStatusConfirm(null);}}} title={`${statusConfirm?.label} договор?`} message="Вы уверены?" isLoading={statusMutation.isPending} confirmLabel={statusConfirm?.label || 'Подтвердить'} confirmVariant="primary"/>
      <ConfirmDialog
        isOpen={bulkGenerateOpen}
        onClose={() => setBulkGenerateOpen(false)}
        onConfirm={() => bulkGenerateMutation.mutate()}
        title="Сгенерировать начисления?"
        message={`Запустить генерацию для ${selected.size} выбранных договоров. Черновики и завершённые будут пропущены.`}
        isLoading={bulkGenerateMutation.isPending}
        confirmLabel="Сгенерировать"
        confirmVariant="primary"
      />
      <BulkExportDialog
        isOpen={bulkExportOpen}
        onClose={() => setBulkExportOpen(false)}
        contractIds={selectedIds}
      />
    </div>
  );
}
