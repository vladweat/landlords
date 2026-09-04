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
import type { Property } from '@/entities/property';
import { Button } from '@/shared/ui/Button';
import { EmptyState } from '@/shared/ui/EmptyState';
import { ActionMenu } from '@/shared/ui/ActionMenu';
import { PropertyModal } from './PropertyModal';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { useHotkeys } from '@/shared/hooks/useHotkeys';
import { TableSkeleton } from '@/shared/ui/Skeleton';
import { exportCSV } from '@/shared/lib/exportCSV';
import { ROIBadge } from '@/features/properties/components/ROIBadge';

const typeLabels: Record<string, string> = { apartment: 'Квартира', house: 'Дом', commercial: 'Коммерческая' };
const PER_PAGE = 20;

export default function PropertiesPage() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState<Property | null>(null);
  const [deleting, setDeleting] = useState<Property | null>(null);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebounce(search, 300);
  useHotkeys({ n: () => { setEditing(null); setIsModalOpen(true); } });

  const { data: paginated, isLoading } = useQuery({
    queryKey: ['properties', page, debouncedSearch, typeFilter],
    queryFn: () => propertiesApi.getAll({ page, per_page: PER_PAGE, search: debouncedSearch || undefined, type: typeFilter !== 'all' ? typeFilter : undefined, sort_by: 'address', sort_dir: 'asc' }),
  });
  const { data: contractsData } = useQuery({ queryKey: ['contracts'], queryFn: () => contractsApi.getAll({ per_page: 100 }), staleTime: 10*60*1000 });

  const properties = paginated?.items || [];
  const contracts = contractsData?.items || [];

  const contractByProperty = useMemo(() => {
    const map: Record<string, { id: string; status: string; end_date: string }> = {};
    contracts.forEach((c) => { if (c.status === 'active' || c.status === 'overdue') map[c.property_id] = { id: c.id, status: c.status, end_date: c.end_date }; });
    return map;
  }, [contracts]);

  const deleteMutation = useMutation({
    mutationFn: propertiesApi.delete,
    onSuccess: () => { scrollToTop(); queryClient.invalidateQueries({ queryKey: ['properties'] }); setDeleting(null); toast.success('Объект удалён'); },
    onError: (error) => showError(error, 'Ошибка удаления'),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Объекты</h1>
        <div className="flex items-center gap-2">
          <button onClick={() => exportCSV(properties, 'objects', ['Адрес','Тип','Площадь'], ['address','type','size_m2'])} className="rounded-lg p-2 text-gray-400 hover:bg-gray-100" title="Экспорт CSV"><Download className="h-4 w-4" /></button>
          <Button onClick={() => { setEditing(null); setIsModalOpen(true); }} leftIcon={<Plus className="h-4 w-4" />}>Добавить</Button>
        </div>
      </div>
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1"><Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input placeholder="Поиск по адресу..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} className="w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }} className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
          <option value="all">Все типы</option><option value="apartment">Квартира</option><option value="house">Дом</option><option value="commercial">Коммерческая</option>
        </select>
      </div>
      {isLoading ? <TableSkeleton rows={5} cols={5} /> : properties.length === 0 ? (
        <EmptyState icon={Building2} title={search || typeFilter !== 'all' ? 'Ничего не найдено' : 'Нет объектов'} description={search || typeFilter !== 'all' ? 'Измените параметры поиска' : 'Добавьте первый объект'} action={!search && typeFilter === 'all' ? { label: 'Добавить объект', onClick: () => { setEditing(null); setIsModalOpen(true); } } : undefined} />
      ) : (
        <div className="hidden sm:block overflow-hidden rounded-xl border border-gray-100 bg-white">
          <table className="w-full"><thead><tr className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
            <th className="py-3 px-4 text-left font-medium">Адрес</th><th className="py-3 px-4 text-left font-medium">Статус</th><th className="py-3 px-4 text-left font-medium">Тип</th><th className="py-3 px-4 text-left font-medium">Площадь</th><th className="py-3 px-4 text-left font-medium hidden lg:table-cell">Доходность</th><th className="py-3 px-4 text-right font-medium w-10"></th>
          </tr></thead>
          <tbody className="divide-y divide-gray-100"><AnimatePresence>{properties.map((p) => {
            const contract = contractByProperty[p.id];
            return (
              <motion.tr key={p.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="hover:bg-gray-50 transition-colors">
                <td className="py-3 px-4 text-sm font-medium">
                  <Link to={`/properties/${p.id}`} className="hover:text-blue-600">{p.address}</Link>
                </td>
                <td className="py-3 px-4">
                  {contract ? (
                    <Link to={`/contracts/${contract.id}`} className="inline-flex items-center gap-2 text-sm text-gray-700 hover:text-blue-600">
                      <span className={`w-2 h-2 rounded-full ${contract.status === 'active' ? 'bg-emerald-500' : 'bg-red-500'}`} />{contract.status === 'active' ? 'Сдаётся' : 'Просрочка'}
                    </Link>
                  ) : <span className="inline-flex items-center gap-2 text-sm text-gray-500"><span className="w-2 h-2 rounded-full bg-gray-300" />Свободен</span>}
                </td>
                <td className="py-3 px-4 text-sm text-gray-700">{typeLabels[p.type]}</td>
                <td className="py-3 px-4 text-sm text-gray-700">{p.size_m2} м²</td>
                <td className="py-3 px-4 hidden lg:table-cell"><ROIBadge roi={p.roi?.roi ?? null} /></td>
                <td className="py-3 px-4 text-right">
                  <ActionMenu items={[
                    { label: 'Редактировать', icon: <Pencil className="h-4 w-4" />, onClick: () => { setEditing(p); setIsModalOpen(true); } },
                    { label: 'Удалить', icon: <Trash2 className="h-4 w-4" />, danger: true, onClick: () => setDeleting(p) },
                  ]} />
                </td>
              </motion.tr>
            );
          })}</AnimatePresence></tbody></table>
        </div>
      )}
      <PropertyModal isOpen={isModalOpen} onClose={() => { setIsModalOpen(false); setEditing(null); }} property={editing} />
      <ConfirmDialog isOpen={!!deleting} onClose={() => setDeleting(null)} onConfirm={() => deleting && deleteMutation.mutate(deleting.id)} title="Удалить объект?" message={`Удалить "${deleting?.address}"?`} isLoading={deleteMutation.isPending} />
    </div>
  );
}
