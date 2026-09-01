import { useState, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Pencil, Trash2, Play, Check, XCircle, Filter, ExternalLink, FileText, Search, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { showError } from '@/shared/lib/toast';
import { scrollToTop } from '@/shared/lib/scrollToTop';
import { contractsApi } from '@/features/contracts/api';
import { propertiesApi } from '@/features/properties/api';
import { tenantsApi } from '@/features/tenants/api';
import type { Contract } from '@/entities/contract';
import { Button } from '@/shared/ui/Button';
import { EmptyState } from '@/shared/ui/EmptyState';
import { ActionMenu } from '@/shared/ui/ActionMenu';
import { ContractModal } from './ContractModal';
import { TerminateContractWizard } from '@/features/contracts/components/TerminateContractWizard';
import { RenewContractWizard } from '@/features/contracts/components/RenewContractWizard';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { useHotkeys } from '@/shared/hooks/useHotkeys';
import { useDebounce } from '@/shared/hooks/useDebounce';
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

export default function ContractsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
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
  const debouncedSearch = useDebounce(search, 300);
  useHotkeys({ n: () => { setEditing(null); setIsModalOpen(true); } });

  const { data: paginated, isLoading } = useQuery({
    queryKey: ['contracts', page, statusFilter, debouncedSearch],
    queryFn: () => contractsApi.getAll({ page, per_page: PER_PAGE, status: statusFilter !== 'all' ? statusFilter : undefined, search: debouncedSearch || undefined }),
  });
  const { data: propertiesData } = useQuery({ queryKey: ['properties'], queryFn: () => propertiesApi.getAll({ per_page: 100 }), staleTime: 10*60*1000 });
  const { data: tenantsData } = useQuery({ queryKey: ['tenants'], queryFn: () => tenantsApi.getAll({ per_page: 100 }), staleTime: 10*60*1000 });

  const contracts = paginated?.items || [];
  const properties = propertiesData?.items || [];
  const tenants = tenantsData?.items || [];

  const pMap = useMemo(() => { const m: Record<string, string> = {}; properties.forEach((p) => m[p.id] = p.address); return m; }, [properties]);
  const tMap = useMemo(() => { const m: Record<string, string> = {}; tenants.forEach((t) => m[t.id] = t.full_name); return m; }, [tenants]);

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

  const Spinner = () => <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Договоры</h1>
        <Button onClick={() => { setEditing(null); setIsModalOpen(true); }} leftIcon={<Plus className="h-4 w-4" />}>Добавить</Button>
      </div>
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1"><Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input placeholder="Поиск..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} className="w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>
      <div className="flex flex-nowrap items-center gap-2 overflow-x-auto pb-2 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden"><Filter className="h-4 w-4 text-gray-400 flex-shrink-0" />
        {[{ value: 'all', label: 'Все' },{ value: 'draft', label: 'Черновики' },{ value: 'active', label: 'Активные' },{ value: 'overdue', label: 'Просрочены' },{ value: 'ended', label: 'Завершены' },{ value: 'terminated', label: 'Расторгнуты' }].map(({ value, label }) => (
          <button key={value} onClick={() => { setStatusFilter(value); setPage(1); }} className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium whitespace-nowrap ${statusFilter === value ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>{label}</button>
        ))}
      </div>
      {isLoading ? <TableSkeleton rows={5} cols={5} /> : contracts.length === 0 ? (
        <EmptyState icon={FileText} title={statusFilter !== 'all' || search ? 'Ничего не найдено' : 'Нет договоров'} description={statusFilter === 'all' && !search ? 'Создайте договор, чтобы начать учёт начислений и платежей' : 'Измените параметры поиска или фильтра'} action={statusFilter === 'all' && !search ? { label: 'Создать договор', onClick: () => { setEditing(null); setIsModalOpen(true); } } : undefined} />
      ) : (
        <div className="hidden sm:block overflow-hidden rounded-xl border border-gray-100 bg-white"><div className="overflow-x-auto"><table className="w-full"><thead><tr className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
          <th className="py-3 px-4 text-left font-medium">Объект</th><th className="py-3 px-4 text-left font-medium">Арендатор</th><th className="py-3 px-4 text-left font-medium">Сумма</th><th className="py-3 px-4 text-left font-medium">Статус</th><th className="py-3 px-4 text-right font-medium w-10"></th>
        </tr></thead>
        <tbody className="divide-y divide-gray-100"><AnimatePresence>{contracts.map((c) => (
          <motion.tr key={c.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="hover:bg-gray-50 transition-colors">
            <td className="py-3 px-4 text-sm font-medium"><button onClick={() => navigate(`/contracts/${c.id}`)} className="hover:text-blue-600 flex items-center gap-1">{shortAddress(pMap[c.property_id]||c.property_id)}<ExternalLink className="h-3 w-3 opacity-50" /></button></td>
            <td className="py-3 px-4 text-sm text-gray-700">{tMap[c.tenant_id]||c.tenant_id}</td>
            <td className="py-3 px-4 text-sm text-gray-700">{Number(c.rent_amount).toLocaleString('ru-RU')} {c.currency}</td>
            <td className="py-3 px-4"><span className="inline-flex items-center gap-2 text-sm text-gray-700"><span className={`w-2 h-2 rounded-full ${statusConfig[c.status]?.color || 'bg-gray-400'}`} />{statusConfig[c.status]?.label || c.status}</span></td>
            <td className="py-3 px-4 text-right">
              <ActionMenu items={[
                ...(c.status === 'draft' ? [{ label: 'Активировать', icon: changingStatus === c.id ? <Spinner/> : <Play className="h-4 w-4" />, onClick: () => setStatusConfirm({id:c.id,status:'active',label:'Активировать'}) }] : []),
                ...(c.status === 'active' || c.status === 'overdue' ? [{ label: 'Завершить', icon: changingStatus === c.id ? <Spinner/> : <Check className="h-4 w-4" />, onClick: () => setStatusConfirm({id:c.id,status:'ended',label:'Завершить'}) }] : []),
                ...(c.status === 'active' || c.status === 'overdue' || c.status === 'ended' ? [{ label: 'Продлить', icon: <RefreshCw className="h-4 w-4" />, onClick: () => setRenewing(c) }] : []),
                ...(c.status === 'draft' || c.status === 'active' || c.status === 'overdue' ? [{ label: 'Расторгнуть', icon: <XCircle className="h-4 w-4" />, onClick: () => setTerminating(c) }] : []),
                { label: 'Редактировать', icon: <Pencil className="h-4 w-4" />, onClick: () => { setEditing(c); setIsModalOpen(true); } },
                { label: 'Удалить', icon: <Trash2 className="h-4 w-4" />, danger: true, onClick: () => setDeleting(c) },
              ]} />
            </td>
          </motion.tr>
        ))}</AnimatePresence></tbody></table></div></div>
      )}
      <ContractModal isOpen={isModalOpen} onClose={()=>{setIsModalOpen(false);setEditing(null)}} contract={editing}/>
      <TerminateContractWizard isOpen={!!terminating} onClose={() => setTerminating(null)} contract={terminating} />
      <RenewContractWizard isOpen={!!renewing} onClose={() => setRenewing(null)} contract={renewing} />
      <ConfirmDialog isOpen={!!deleting} onClose={()=>setDeleting(null)} onConfirm={()=>deleting&&deleteMutation.mutate(deleting.id)} title="Удалить договор?" message="Вы уверены?" isLoading={deleteMutation.isPending}/>
      <ConfirmDialog isOpen={!!statusConfirm} onClose={()=>setStatusConfirm(null)} onConfirm={()=>{if(statusConfirm){statusMutation.mutate({id:statusConfirm.id,status:statusConfirm.status});setStatusConfirm(null);}}} title={`${statusConfirm?.label} договор?`} message="Вы уверены?" isLoading={statusMutation.isPending}/>
    </div>
  );
}
