import { scrollToTop } from '@/shared/lib/scrollToTop';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { toast } from 'sonner';
import { showError } from '@/shared/lib/toast';
import { useEscapeKey } from '@/shared/hooks/useEscapeKey';
import { expensesApi } from '@/features/expenses/api';
import { propertiesApi } from '@/features/properties/api';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { shortAddress } from '@/shared/lib/address';
import { EXPENSE_CATEGORY_LABELS, type ExpenseCategory } from '@/entities/expense';
import { z } from 'zod';

const expenseSchema = z.object({
  property_id: z.string().min(1, 'Выберите объект'),
  category: z.enum(['utilities', 'repair', 'tax', 'realtor_fee', 'other'], {
    message: 'Выберите категорию',
  }),
  amount: z
    .string()
    .min(1, 'Укажите сумму')
    .refine((v) => !Number.isNaN(Number(v)) && Number(v) > 0, 'Сумма должна быть больше 0'),
  date_incurred: z.string().min(1, 'Выберите дату'),
  note: z.string().optional(),
});

type ExpenseFormData = z.infer<typeof expenseSchema>;

interface ExpenseModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ExpenseModal({ isOpen, onClose }: ExpenseModalProps) {
  const queryClient = useQueryClient();
  useEscapeKey(onClose);

  const { data: propertiesData } = useQuery({
    queryKey: ['properties'],
    queryFn: () => propertiesApi.getAll({ per_page: 100 }),
    enabled: isOpen,
  });
  const properties = propertiesData?.items || [];

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ExpenseFormData>({
    resolver: zodResolver(expenseSchema),
    defaultValues: {
      property_id: '',
      category: 'utilities',
      amount: '',
      date_incurred: '',
      note: '',
    },
  });

  useEffect(() => {
    if (!isOpen) {
      reset({
        property_id: '',
        category: 'utilities',
        amount: '',
        date_incurred: '',
        note: '',
      });
    }
  }, [isOpen, reset]);

  const createMutation = useMutation({
    mutationFn: expensesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
      queryClient.invalidateQueries({ queryKey: ['properties'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      scrollToTop();
      toast.success('Расход добавлен');
      onClose();
    },
    onError: (error) => showError(error, 'Ошибка создания'),
  });

  const onSubmit = (data: ExpenseFormData) =>
    createMutation.mutate({
      property_id: data.property_id,
      category: data.category as ExpenseCategory,
      amount: data.amount,
      date_incurred: data.date_incurred,
      note: data.note || undefined,
    });

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
                <h2 className="text-lg font-semibold text-gray-900">Новый расход</h2>
                <button onClick={onClose} className="rounded-lg p-1 text-gray-400 hover:bg-gray-100">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <div className="w-full">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Объект</label>
                  <select
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    {...register('property_id')}
                  >
                    <option value="">Выберите объект</option>
                    {properties.map((p) => (
                      <option key={p.id} value={p.id}>
                        {shortAddress(p.address)}
                      </option>
                    ))}
                  </select>
                  {errors.property_id && (
                    <p className="mt-1 text-sm text-red-600">{errors.property_id.message}</p>
                  )}
                </div>
                <div className="w-full">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Категория</label>
                  <select
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    {...register('category')}
                  >
                    {(Object.keys(EXPENSE_CATEGORY_LABELS) as ExpenseCategory[]).map((key) => (
                      <option key={key} value={key}>
                        {EXPENSE_CATEGORY_LABELS[key]}
                      </option>
                    ))}
                  </select>
                </div>
                <Input
                  label="Сумма"
                  type="number"
                  error={errors.amount?.message}
                  {...register('amount')}
                />
                <Input
                  label="Дата"
                  type="date"
                  error={errors.date_incurred?.message}
                  {...register('date_incurred')}
                />
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
