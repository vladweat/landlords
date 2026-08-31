import { scrollToTop } from "@/shared/lib/scrollToTop";
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { toast } from 'sonner';
import { showError } from '@/shared/lib/toast';
import { useEscapeKey } from '@/shared/hooks/useEscapeKey';
import { contractsApi } from '@/features/contracts/api';
import type { Contract } from '@/entities/contract';
import { propertiesApi } from '@/features/properties/api';
import { tenantsApi } from '@/features/tenants/api';
import { CreditScoreBadge } from '@/features/tenants/components/CreditScoreBadge';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { z } from 'zod';

const contractSchema = z.object({
  property_id: z.string().min(1), tenant_id: z.string().min(1), rent_amount: z.coerce.number().min(1),
  currency: z.string().min(1), start_date: z.string().min(1), end_date: z.string().min(1),
  payment_day: z.coerce.number().min(1).max(31), billing_period: z.string().min(1),
  deposit_amount: z.coerce.number().nullable(), auto_generate_charges: z.boolean(),
});
type ContractFormData = z.infer<typeof contractSchema>;

interface ContractModalProps { isOpen: boolean; onClose: () => void; contract: Contract | null; }

export function ContractModal({ isOpen, onClose, contract }: ContractModalProps) {
  const queryClient = useQueryClient();
  useEscapeKey(onClose);
  const [selectedTenantId, setSelectedTenantId] = useState<string>('');

  const { data: propertiesData } = useQuery({ queryKey: ['properties'], queryFn: () => propertiesApi.getAll({ per_page: 100 }), enabled: isOpen });
  const { data: tenantsData } = useQuery({ queryKey: ['tenants'], queryFn: () => tenantsApi.getAll({ per_page: 100 }), enabled: isOpen });

  const properties = propertiesData?.items || [];
  const tenants = tenantsData?.items || [];

  const { data: tenantScore } = useQuery({
    queryKey: ['tenant-score', selectedTenantId],
    queryFn: () => tenantsApi.getScore(selectedTenantId),
    enabled: !!selectedTenantId,
  });

  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<ContractFormData>({
    resolver: zodResolver(contractSchema),
    defaultValues: { property_id: '', tenant_id: '', rent_amount: undefined, currency: 'RUB', start_date: '', end_date: '', payment_day: 1, billing_period: 'monthly', deposit_amount: undefined, auto_generate_charges: false },
  });

  const watchedTenantId = watch('tenant_id');

  useEffect(() => {
    setSelectedTenantId(watchedTenantId);
  }, [watchedTenantId]);

  useEffect(() => {
    reset(contract ? {
      property_id: contract.property_id, tenant_id: contract.tenant_id, rent_amount: Number(contract.rent_amount),
      currency: contract.currency, start_date: contract.start_date?.split('T')[0] || '', end_date: contract.end_date?.split('T')[0] || '',
      payment_day: contract.payment_day, billing_period: contract.billing_period,
      deposit_amount: contract.deposit_amount ? Number(contract.deposit_amount) : null, auto_generate_charges: contract.auto_generate_charges,
    } : { property_id: '', tenant_id: '', rent_amount: undefined, currency: 'RUB', start_date: '', end_date: '', payment_day: 1, billing_period: 'monthly', deposit_amount: undefined, auto_generate_charges: false });
  }, [contract, reset]);

  const createMutation = useMutation({
    mutationFn: contractsApi.create,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['contracts'] }); scrollToTop(); toast.success("Договор добавлен"); onClose(); },
    onError: (error) => showError(error, 'Ошибка создания'),
  });

  const updateMutation = useMutation({
    mutationFn: (data: ContractFormData) => contract ? contractsApi.update(contract.id, data) : Promise.reject(),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['contracts'] }); toast.success('Договор обновлён'); onClose(); },
    onError: (error) => showError(error, 'Ошибка обновления'),
  });

  const onSubmit = (data: ContractFormData) => {
    const payload = { ...data, deposit_amount: data.deposit_amount || null };
    contract ? updateMutation.mutate(payload) : createMutation.mutate(payload);
  };
  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 bg-black/50" onClick={onClose} />
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl max-h-[80vh] overflow-y-auto [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">{contract ? 'Редактировать договор' : 'Новый договор'}</h2>
                <button onClick={onClose} className="rounded-lg p-1 text-gray-400 hover:bg-gray-100"><X className="h-5 w-5" /></button>
              </div>
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <div className="w-full"><label className="block text-sm font-medium text-gray-700 mb-1">Объект</label>
                  <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" {...register('property_id')}>
                    <option value="">Выберите объект</option>{properties.map((p) => <option key={p.id} value={p.id}>{p.address}</option>)}
                  </select>
                </div>
                <div className="w-full"><label className="block text-sm font-medium text-gray-700 mb-1">Арендатор</label>
                  <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" {...register('tenant_id')}>
                    <option value="">Выберите арендатора</option>{tenants.map((t) => <option key={t.id} value={t.id}>{t.full_name}</option>)}
                  </select>
                  {selectedTenantId && tenantScore && (
                    <div className="mt-2 flex items-center gap-3 text-sm bg-gray-50 rounded-lg p-2">
                      <CreditScoreBadge score={tenantScore.score} />
                      {tenantScore.metrics.total_payments > 0 && (
                        <span className="text-gray-500">
                          Задержка: <span className="font-medium">{tenantScore.metrics.avg_delay_days} дн.</span> · Платежей: {tenantScore.metrics.total_payments}
                        </span>
                      )}
                    </div>
                  )}
                </div>
                <Input label="Сумма аренды" type="number" error={errors.rent_amount?.message} {...register('rent_amount')} />
                <div className="w-full"><label className="block text-sm font-medium text-gray-700 mb-1">Валюта</label>
                  <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" {...register('currency')}>
                    <option value="RUB">RUB</option><option value="USD">USD</option><option value="EUR">EUR</option>
                  </select>
                </div>
                <div className="w-full"><label className="block text-sm font-medium text-gray-700 mb-1">Период оплаты</label>
                  <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" {...register('billing_period')}>
                    <option value="monthly">Ежемесячно</option><option value="quarterly">Ежеквартально</option><option value="yearly">Ежегодно</option>
                  </select>
                </div>
                <Input label="День платежа" type="number" error={errors.payment_day?.message} {...register('payment_day')} />
                <Input label="Депозит" type="number" placeholder="Необязательно" error={errors.deposit_amount?.message} {...register('deposit_amount')} />
                <Input label="Дата начала" type="date" error={errors.start_date?.message} {...register('start_date')} />
                <Input label="Дата окончания" type="date" error={errors.end_date?.message} {...register('end_date')} />
                <label className="flex items-center gap-2"><input type="checkbox" {...register('auto_generate_charges')} className="rounded border-gray-300" /><span className="text-sm text-gray-700">Авто-начисления</span></label>
                <div className="flex gap-3 pt-2">
                  <Button type="button" variant="secondary" onClick={onClose} className="flex-1">Отмена</Button>
                  <Button type="submit" className="flex-1" isLoading={isPending}>{contract ? 'Сохранить' : 'Добавить'}</Button>
                </div>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
