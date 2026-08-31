import { scrollToTop } from "@/shared/lib/scrollToTop";
import { getContractLabel } from "@/shared/lib/contractLabel";
import { useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { toast } from 'sonner';
import { showError } from '@/shared/lib/toast';
import { useEscapeKey } from '@/shared/hooks/useEscapeKey';
import { paymentsApi } from '@/features/payments/api';
import { contractsApi } from '@/features/contracts/api';
import { propertiesApi } from '@/features/properties/api';
import { tenantsApi } from '@/features/tenants/api';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { z } from 'zod';

const paymentSchema = z.object({
  contract_id: z.string().min(1, 'Выберите договор'),
  amount: z.coerce.number().min(1, 'Сумма должна быть больше 0'),
  date_paid: z.string().min(1, 'Выберите дату'),
  method: z.string().min(1, 'Выберите способ'),
  note: z.string().optional(),
  charge_id: z.string().optional(),
});

type PaymentFormData = z.infer<typeof paymentSchema>;

interface PaymentModalProps { isOpen: boolean; onClose: () => void; }

export function PaymentModal({ isOpen, onClose }: PaymentModalProps) {
  const queryClient = useQueryClient();
  useEscapeKey(onClose);
  const [selectedContract, setSelectedContract] = useState('');

  const { data: contractsData } = useQuery({ queryKey: ['contracts'], queryFn: () => contractsApi.getAll({ per_page: 100 }), enabled: isOpen });
  const { data: propertiesData } = useQuery({ queryKey: ['properties'], queryFn: () => propertiesApi.getAll({ per_page: 100 }), enabled: isOpen });
  const { data: tenantsData } = useQuery({ queryKey: ['tenants'], queryFn: () => tenantsApi.getAll({ per_page: 100 }), enabled: isOpen });
  const { data: charges } = useQuery({ queryKey: ['charges', selectedContract], queryFn: () => paymentsApi.getCharges(selectedContract), enabled: !!selectedContract });

  const contracts = contractsData?.items || [];
  const properties = propertiesData?.items || [];
  const tenants = tenantsData?.items || [];

  const activeContracts = useMemo(() => contracts.filter((c) => c.status === 'active' || c.status === 'draft' || c.status === 'overdue'), [contracts]);
  const pendingCharges = useMemo(() => (charges || []).filter((c: { status: string }) => c.status === 'pending' || c.status === 'overdue'), [charges]);

  const { register, handleSubmit, reset, watch, setValue, formState: { errors } } = useForm<PaymentFormData>({
    resolver: zodResolver(paymentSchema),
    defaultValues: { contract_id: '', amount: undefined, date_paid: '', method: 'transfer', note: '', charge_id: '' },
  });

  const contractId = watch('contract_id');
  const selectedChargeId = watch('charge_id');

  useEffect(() => {
    setSelectedContract(contractId);
    setValue('charge_id', '');
    setValue('amount', undefined);
  }, [contractId, setValue]);

  useEffect(() => {
    if (selectedChargeId && pendingCharges.length > 0) {
      const charge = pendingCharges.find((c: { id: string; amount: string }) => c.id === selectedChargeId);
      if (charge) setValue('amount', Number(charge.amount));
    }
  }, [selectedChargeId, pendingCharges, setValue]);

  useEffect(() => {
    if (!isOpen) reset({ contract_id: '', amount: undefined, date_paid: '', method: 'transfer', note: '', charge_id: '' });
  }, [isOpen, reset]);

  const createMutation = useMutation({
    mutationFn: paymentsApi.create,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['payments'] }); queryClient.invalidateQueries({ queryKey: ['charges', selectedContract] }); scrollToTop(); toast.success("Платёж добавлен"); onClose(); },
    onError: (error) => showError(error, 'Ошибка создания'),
  });

  const onSubmit = (data: PaymentFormData) => createMutation.mutate({ contract_id: data.contract_id, amount: data.amount, date_paid: data.date_paid, method: data.method, note: data.note || undefined, rent_charge_id: data.charge_id || undefined });


  const maxAmount = selectedChargeId ? Number(pendingCharges.find((c: { id: string; amount: string }) => c.id === selectedChargeId)?.amount || 0) : undefined;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 bg-black/50" onClick={onClose} />
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl max-h-[80vh] overflow-y-auto [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">Новый платёж</h2>
                <button onClick={onClose} className="rounded-lg p-1 text-gray-400 hover:bg-gray-100"><X className="h-5 w-5" /></button>
              </div>
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <div className="w-full">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Договор</label>
                  <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" {...register('contract_id')}>
                    <option value="">Выберите договор</option>
                    {activeContracts.map((c) => <option key={c.id} value={c.id}>{getContractLabel(c, properties, tenants)}</option>)}
                  </select>
                  {errors.contract_id && <p className="mt-1 text-sm text-red-600">{errors.contract_id.message}</p>}
                </div>
                {pendingCharges.length > 0 && (
                  <div className="w-full">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Начисление (необязательно)</label>
                    <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" {...register('charge_id')}>
                      <option value="">Без привязки</option>
                      {pendingCharges.map((c: { id: string; due_date: string; amount: string }) => (
                        <option key={c.id} value={c.id}>{c.due_date} — {Number(c.amount).toLocaleString('ru-RU')} ₽</option>
                      ))}
                    </select>
                  </div>
                )}
                <Input label={`Сумма${maxAmount ? ` (макс. ${maxAmount.toLocaleString('ru-RU')} ₽)` : ''}`} type="number" error={errors.amount?.message} {...register('amount')} />
                <Input label="Дата платежа" type="date" error={errors.date_paid?.message} {...register('date_paid')} />
                <div className="w-full">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Способ оплаты</label>
                  <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" {...register('method')}>
                    <option value="transfer">Перевод</option><option value="cash">Наличные</option><option value="card">Карта</option>
                  </select>
                </div>
                <Input label="Примечание" placeholder="Необязательно" {...register('note')} />
                <div className="flex gap-3 pt-2">
                  <Button type="button" variant="secondary" onClick={onClose} className="flex-1">Отмена</Button>
                  <Button type="submit" className="flex-1" isLoading={createMutation.isPending}>Добавить</Button>
                </div>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
