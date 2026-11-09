import { useEffect, useMemo, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { toast } from 'sonner';
import { scrollToTop } from '@/shared/lib/scrollToTop';
import { getContractLabel } from '@/shared/lib/contractLabel';
import { showError, showSuccess } from '@/shared/lib/toast';
import { useEscapeKey } from '@/shared/hooks/useEscapeKey';
import { createPaymentIdempotencyManager, paymentsApi } from '@/features/payments/api';
import { contractsApi } from '@/features/contracts/api';
import { propertiesApi } from '@/features/properties/api';
import { tenantsApi } from '@/features/tenants/api';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { z } from 'zod';

const UNPAID_STATUSES = new Set(['pending', 'overdue', 'partially_paid']);

type ChargeOption = {
  id: string;
  due_date: string;
  amount: string;
  amount_paid?: string;
  status: string;
};

function chargeRemaining(charge: ChargeOption): number {
  const amount = Number(charge.amount);
  const paid = Number(charge.amount_paid || 0);
  return Math.max(0, amount - paid);
}

function todayISO(): string {
  const today = new Date();
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
}

const paymentSchema = z.object({
  contract_id: z.string().min(1, 'Выберите договор'),
  amount: z
    .string()
    .min(1, 'Укажите сумму')
    .refine((v) => !Number.isNaN(Number(v)) && Number(v) > 0, 'Сумма должна быть больше 0'),
  date_paid: z.string().min(1, 'Выберите дату'),
  method: z.string().min(1, 'Выберите способ'),
  note: z.string().optional(),
  rent_charge_id: z.string().optional(),
});

type PaymentFormData = z.infer<typeof paymentSchema>;

interface PaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultContractId?: string;
  defaultChargeId?: string;
}

export function PaymentModal({ isOpen, onClose, defaultContractId, defaultChargeId }: PaymentModalProps) {
  const queryClient = useQueryClient();
  useEscapeKey(onClose);
  const [selectedContract, setSelectedContract] = useState('');
  const paymentIdempotencyRef = useRef<ReturnType<typeof createPaymentIdempotencyManager> | null>(null);
  if (paymentIdempotencyRef.current === null) {
    paymentIdempotencyRef.current = createPaymentIdempotencyManager();
  }

  const { data: contractsData } = useQuery({
    queryKey: ['contracts'],
    queryFn: () => contractsApi.getAll({ per_page: 100 }),
    enabled: isOpen,
  });
  const { data: propertiesData } = useQuery({
    queryKey: ['properties'],
    queryFn: () => propertiesApi.getAll({ per_page: 100 }),
    enabled: isOpen,
  });
  const { data: tenantsData } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantsApi.getAll({ per_page: 100 }),
    enabled: isOpen,
  });
  const { data: charges } = useQuery({
    queryKey: ['charges', selectedContract],
    queryFn: () => paymentsApi.getCharges(selectedContract),
    enabled: !!selectedContract,
  });

  const contracts = contractsData?.items || [];
  const properties = propertiesData?.items || [];
  const tenants = tenantsData?.items || [];

  const activeContracts = useMemo(
    () => contracts.filter((c) => c.status === 'active' || c.status === 'draft' || c.status === 'overdue'),
    [contracts],
  );
  const unpaidCharges = useMemo(
    () => ((charges || []) as ChargeOption[]).filter((c) => UNPAID_STATUSES.has(c.status)),
    [charges],
  );

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors },
  } = useForm<PaymentFormData>({
    resolver: zodResolver(paymentSchema),
    defaultValues: {
      contract_id: '',
      amount: '',
      date_paid: '',
      method: 'transfer',
      note: '',
      rent_charge_id: '',
    },
  });

  const selectedChargeId = watch('rent_charge_id');
  const watchedContractId = watch('contract_id');

  const contractOptions = useMemo(() => {
    const list = [...activeContracts];
    if (defaultContractId && !list.some((c) => c.id === defaultContractId)) {
      const found = contracts.find((c) => c.id === defaultContractId);
      if (found) list.unshift(found);
    }
    return list;
  }, [activeContracts, contracts, defaultContractId]);

  useEffect(() => {
    if (!isOpen) return;
    reset({
      contract_id: defaultContractId || '',
      amount: '',
      date_paid: todayISO(),
      method: 'transfer',
      note: '',
      rent_charge_id: defaultChargeId || '',
    });
    setSelectedContract(defaultContractId || '');
  }, [isOpen, defaultContractId, defaultChargeId, reset]);

  // После загрузки options HTML select иначе может «сбросить» value визуально
  useEffect(() => {
    if (!isOpen || !defaultContractId || contractOptions.length === 0) return;
    if (!contractOptions.some((c) => c.id === defaultContractId)) return;
    setValue('contract_id', defaultContractId, { shouldDirty: false });
    setSelectedContract(defaultContractId);
  }, [isOpen, defaultContractId, contractOptions, setValue]);

  useEffect(() => {
    if (!selectedChargeId || unpaidCharges.length === 0) return;
    const charge = unpaidCharges.find((c) => c.id === selectedChargeId);
    if (!charge) return;
    const remaining = chargeRemaining(charge);
    if (remaining > 0) setValue('amount', String(remaining));
  }, [selectedChargeId, unpaidCharges, setValue]);

  const createMutation = useMutation({
    mutationFn: (data: PaymentFormData) =>
      paymentsApi.create(data, paymentIdempotencyRef.current!.keyFor(data)),
    retry: 0,
    onSuccess: (result) => {
      paymentIdempotencyRef.current?.complete();
      queryClient.invalidateQueries({ queryKey: ['payments'] });
      queryClient.invalidateQueries({ queryKey: ['charges', selectedContract] });
      queryClient.invalidateQueries({ queryKey: ['contract-charges', selectedContract] });
      queryClient.invalidateQueries({ queryKey: ['contract-ledger', selectedContract] });
      queryClient.invalidateQueries({ queryKey: ['contract', selectedContract] });
      queryClient.invalidateQueries({ queryKey: ['contract-events'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-last-payments'] });
      scrollToTop();
      if (result.payments.length > 1) {
        showSuccess(`Платёж распределён на ${result.payments.length} записи`);
      } else {
        showSuccess('Платёж добавлен');
      }
      onClose();
    },
    onError: (error) => showError(error, 'Ошибка создания'),
  });

  const selectedCharge = unpaidCharges.find((c) => c.id === selectedChargeId);
  const maxAmount = selectedCharge ? chargeRemaining(selectedCharge) : undefined;

  const contractRegister = register('contract_id');

  const onSubmit = (data: PaymentFormData) => {
    if (maxAmount !== undefined && Number(data.amount) > maxAmount) {
      toast.error(`Сумма не должна превышать остаток ${maxAmount.toLocaleString('ru-RU')} ₽`);
      return;
    }
    createMutation.mutate({
      contract_id: data.contract_id,
      amount: data.amount,
      date_paid: data.date_paid,
      method: data.method,
      note: data.note || undefined,
      rent_charge_id: data.rent_charge_id || undefined,
    });
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
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl max-h-[80vh] overflow-y-auto [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">Новый платёж</h2>
                <button onClick={onClose} className="rounded-lg p-1 text-gray-400 hover:bg-gray-100">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <div className="w-full">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Договор</label>
                  <select
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    {...contractRegister}
                    value={watchedContractId || ''}
                    onChange={(e) => {
                      contractRegister.onChange(e);
                      setSelectedContract(e.target.value);
                      setValue('rent_charge_id', '');
                      setValue('amount', '');
                    }}
                  >
                    <option value="">Выберите договор</option>
                    {contractOptions.map((c) => (
                      <option key={c.id} value={c.id}>
                        {getContractLabel(c, properties, tenants)}
                      </option>
                    ))}
                  </select>
                  {errors.contract_id && (
                    <p className="mt-1 text-sm text-red-600">{errors.contract_id.message}</p>
                  )}
                </div>
                {unpaidCharges.length > 0 && (
                  <div className="w-full">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Начисление (необязательно)
                    </label>
                    <select
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                      {...register('rent_charge_id')}
                    >
                      <option value="">Без привязки (автораспределение)</option>
                      {unpaidCharges.map((c) => {
                        const remaining = chargeRemaining(c);
                        const partial = c.status === 'partially_paid' || Number(c.amount_paid || 0) > 0;
                        const label = partial
                          ? `${c.due_date} — остаток ${remaining.toLocaleString('ru-RU')} ₽ (частично)`
                          : `${c.due_date} — ${remaining.toLocaleString('ru-RU')} ₽`;
                        return (
                          <option key={c.id} value={c.id}>
                            {label}
                          </option>
                        );
                      })}
                    </select>
                  </div>
                )}
                <Input
                  label={`Сумма${maxAmount !== undefined ? ` (макс. ${maxAmount.toLocaleString('ru-RU')} ₽)` : ''}`}
                  type="number"
                  step="0.01"
                  max={maxAmount}
                  error={errors.amount?.message}
                  {...register('amount')}
                />
                <Input label="Дата платежа" type="date" error={errors.date_paid?.message} {...register('date_paid')} />
                <div className="w-full">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Способ оплаты</label>
                  <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" {...register('method')}>
                    <option value="transfer">Перевод</option>
                    <option value="cash">Наличные</option>
                    <option value="card">Карта</option>
                  </select>
                </div>
                <Input label="Примечание" placeholder="Необязательно" {...register('note')} />
                <div className="flex gap-3 pt-2">
                  <Button type="button" variant="secondary" onClick={onClose} className="flex-1">
                    Отмена
                  </Button>
                  <Button type="submit" className="flex-1" isLoading={createMutation.isPending}>
                    Добавить
                  </Button>
                </div>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
