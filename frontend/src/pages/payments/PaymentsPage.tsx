import { useState, useMemo } from 'react';
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
import { PaymentModal } from './PaymentModal';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { useHotkeys } from '@/shared/hooks/useHotkeys';
import { useSort } from '@/shared/hooks/useSort';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { TableSkeleton } from '@/shared/ui/Skeleton';
import { shortAddress } from '@/shared/lib/address';

const methodLabels: Record<string, string> = { transfer: 'Перевод', cash: 'Наличные', card: 'Карта' };

export default function PaymentsPage() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [deleting, setDeleting] = useState<Payment | null>(null);
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search, 300);
  useHotkeys({ n: () => { setIsModalOpen(true); } });

  const { data: payments, isLoading } = useQuery({ queryKey: ['payments'], queryFn: paymentsApi.getAll });
  const { data: contractsData } = useQuery({ queryKey: ['contracts'], queryFn: () => contractsApi.getAll({ per_page: 100 }), staleTime: 10*60*1000 });
  const { data: propertiesData } = useQuery({ queryKey: ['properties'], queryFn: () => propertiesApi.getAll({ per_page: 100 }), staleTime: 10*60*1000 });
  const { data: tenantsData } = useQuery({ queryKey: ['tenants'], queryFn: () => tenantsApi.getAll({ per_page: 100 }), staleTime: 10*60*1000 });

  const contracts = contractsData?.items || [];
  const properties = propertiesData?.items || [];
  const tenants = tenantsData?.items || [];

  const contractMap = useMemo(() => {
    const m: Record<string, string> = {};
    contracts.forEach((c) => { const p=properties.find((x)=>x.id===c.property_id); const t=tenants.find((x)=>x.id===c.tenant_id); m[c.id]=`${shortAddress(p?.address||'—')} / ${t?.full_name||'—'}`; });
    return m;
  }, [contracts, properties, tenants]);

  const filtered = useMemo(() => {
    if (!payments) return [];
    if (!debouncedSearch) return payments;
    const q = debouncedSearch.toLowerCase();
    return payments.filter((p) => (contractMap[p.contract_id] || '').toLowerCase().includes(q));
  }, [payments, debouncedSearch, contractMap]);

  const { sorted, sortKey, sortDir, toggle } = useSort(filtered);

  const deleteMutation = useMutation({
    mutationFn: paymentsApi.delete,
    onSuccess: () => { scrollToTop(); queryClient.invalidateQueries({ queryKey: ['payments'] }); setDeleting(null); toast.success('Платёж удалён'); },
    onError: (error) => showError(error, 'Ошибка удаления'),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Платежи</h1>
        <Button onClick={() => setIsModalOpen(true)} leftIcon={<Plus className="h-4 w-4" />}>Добавить</Button>
      </div>
      <div className="relative"><Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input placeholder="Поиск по договору..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
      </div>
      {isLoading ? <TableSkeleton rows={5} cols={5} /> : !payments?.length ? (
        <EmptyState icon={CreditCard} title={search ? 'Ничего не найдено' : 'Нет платежей'} description={search ? 'Измените параметры поиска' : 'Платежи появятся после создания договоров и начислений'} />
      ) : (
        <div className="hidden sm:block overflow-hidden rounded-xl border border-gray-100 bg-white"><table className="w-full"><thead><tr className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
          <th className="py-3 px-4 text-left font-medium">Договор</th>
          <th className="py-3 px-4 text-left font-medium cursor-pointer select-none" onClick={() => toggle('amount')}>Сумма {sortKey==='amount'?(sortDir==='asc'?'▲':'▼'):''}</th>
          <th className="py-3 px-4 text-left font-medium">Способ</th>
          <th className="py-3 px-4 text-left font-medium cursor-pointer select-none" onClick={() => toggle('date_paid')}>Дата {sortKey==='date_paid'?(sortDir==='asc'?'▲':'▼'):''}</th>
          <th className="py-3 px-4 text-right font-medium w-10"></th>
        </tr></thead>
        <tbody className="divide-y divide-gray-100"><AnimatePresence>{sorted.map((p) => (
          <motion.tr key={p.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="hover:bg-gray-50 transition-colors">
            <td className="py-3 px-4 text-sm text-gray-700">{contractMap[p.contract_id]||p.contract_id}</td>
            <td className="py-3 px-4 text-sm font-medium text-gray-900">{Number(p.amount).toLocaleString('ru-RU')} {p.currency}</td>
            <td className="py-3 px-4 text-sm text-gray-700">{methodLabels[p.method]||p.method}</td>
            <td className="py-3 px-4 text-sm text-gray-700">{formatDate(p.date_paid)}</td>
            <td className="py-3 px-4 text-right">
              <ActionMenu items={[
                { label: 'Удалить', icon: <Trash2 className="h-4 w-4" />, danger: true, onClick: () => setDeleting(p) },
              ]} />
            </td>
          </motion.tr>
        ))}</AnimatePresence></tbody></table></div>
      )}
      <PaymentModal isOpen={isModalOpen} onClose={()=>setIsModalOpen(false)}/>
      <ConfirmDialog isOpen={!!deleting} onClose={()=>setDeleting(null)} onConfirm={()=>deleting&&deleteMutation.mutate(deleting.id)} title="Удалить платёж?" message={`Удалить платёж на ${deleting?Number(deleting.amount).toLocaleString('ru-RU'):''} ${deleting?.currency||''}?`} isLoading={deleteMutation.isPending}/>
    </div>
  );
}
