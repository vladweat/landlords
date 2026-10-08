import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { X, RefreshCw } from 'lucide-react';
import { z } from 'zod';
import { showError, showSuccess } from '@/shared/lib/toast';
import { useEscapeKey } from '@/shared/hooks/useEscapeKey';
import { contractsApi } from '@/features/contracts/api';
import type { Contract } from '@/entities/contract';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';

const schema = z.object({
  new_end_date: z.string().min(1, 'Укажите новую дату окончания'),
  new_rent_amount: z
    .string()
    .optional()
    .refine((v) => !v || (!Number.isNaN(Number(v)) && Number(v) > 0), 'Сумма должна быть больше 0'),
  generate_act: z.boolean(),
});

type FormData = z.infer<typeof schema>;

interface RenewContractWizardProps {
  isOpen: boolean;
  onClose: () => void;
  contract: Contract | null;
}

export function RenewContractWizard({ isOpen, onClose, contract }: RenewContractWizardProps) {
  const queryClient = useQueryClient();
  const [step, setStep] = useState(1);
  useEscapeKey(onClose);

  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      new_end_date: '',
      new_rent_amount: '',
      generate_act: true,
    },
  });

  const values = watch();

  useEffect(() => {
    if (isOpen && contract) {
      setStep(1);
      const end = new Date(contract.end_date + 'T00:00:00');
      end.setFullYear(end.getFullYear() + 1);
      reset({
        new_end_date: end.toISOString().slice(0, 10),
        new_rent_amount: contract.rent_amount,
        generate_act: true,
      });
    }
  }, [isOpen, contract, reset]);

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      contractsApi.renew(contract!.id, {
        new_end_date: data.new_end_date,
        new_rent_amount: data.new_rent_amount || null,
        generate_act: data.generate_act,
      }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
      queryClient.invalidateQueries({ queryKey: ['contract', contract?.id] });
      queryClient.invalidateQueries({ queryKey: ['contract-charges', contract?.id] });
      queryClient.invalidateQueries({ queryKey: ['contract-ledger', contract?.id] });
      queryClient.invalidateQueries({ queryKey: ['contract-events', contract?.id] });
      showSuccess(
        result.charges_created
          ? `Договор продлён · добавлено начислений: ${result.charges_created}`
          : 'Договор продлён',
      );
      if (result.document_url) {
        window.open(result.document_url, '_blank');
      }
      onClose();
    },
    onError: (error) => showError(error, 'Ошибка продления'),
  });

  if (!contract) return null;

  const onConfirm = handleSubmit((data) => mutation.mutate(data));

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
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100">
                    <RefreshCw className="h-5 w-5 text-blue-700" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">Продление договора</h2>
                    <p className="text-xs text-gray-500">Шаг {step} из 2</p>
                  </div>
                </div>
                <button onClick={onClose} className="text-gray-400 hover:text-gray-600" type="button">
                  <X className="h-5 w-5" />
                </button>
              </div>

              {step === 1 && (
                <form
                  className="space-y-4"
                  onSubmit={handleSubmit(() => setStep(2))}
                >
                  <div className="rounded-lg bg-gray-50 p-3 text-sm text-gray-600">
                    Текущая дата окончания: <span className="font-medium text-gray-900">{contract.end_date}</span>
                  </div>
                  <Input
                    label="Новая дата окончания"
                    type="date"
                    min={contract.end_date}
                    error={errors.new_end_date?.message}
                    {...register('new_end_date')}
                  />
                  <Input
                    label="Арендная плата (опционально)"
                    type="text"
                    inputMode="decimal"
                    error={errors.new_rent_amount?.message}
                    {...register('new_rent_amount')}
                  />
                  <label className="flex items-center gap-2 text-sm text-gray-700">
                    <input type="checkbox" className="rounded border-gray-300" {...register('generate_act')} />
                    Сформировать допсоглашение (PDF)
                  </label>
                  <div className="flex gap-3 pt-2">
                    <Button variant="secondary" type="button" onClick={onClose} className="flex-1">Отмена</Button>
                    <Button type="submit" className="flex-1">Далее</Button>
                  </div>
                </form>
              )}

              {step === 2 && (
                <div className="space-y-4">
                  <div className="rounded-lg bg-gray-50 p-4 text-sm space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Было</span>
                      <span>{contract.end_date}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Станет</span>
                      <span className="font-medium">{values.new_end_date}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Аренда</span>
                      <span>
                        {values.new_rent_amount || contract.rent_amount} {contract.currency}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Допсоглашение</span>
                      <span>{values.generate_act ? 'Да' : 'Нет'}</span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">
                    На продлённый период будут добавлены начисления. Договор останется на том же объекте и арендаторе.
                  </p>
                  <div className="flex gap-3 pt-2">
                    <Button variant="secondary" type="button" onClick={() => setStep(1)} className="flex-1">
                      Назад
                    </Button>
                    <Button type="button" onClick={onConfirm} isLoading={mutation.isPending} className="flex-1">
                      Продлить
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
