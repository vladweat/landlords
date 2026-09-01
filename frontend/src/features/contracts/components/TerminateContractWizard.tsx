import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { X, FileX } from 'lucide-react';
import { toast } from 'sonner';
import { z } from 'zod';
import { showError } from '@/shared/lib/toast';
import { useEscapeKey } from '@/shared/hooks/useEscapeKey';
import { contractsApi } from '@/features/contracts/api';
import type { Contract } from '@/entities/contract';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';

const schema = z.object({
  effective_date: z.string().min(1, 'Укажите дату'),
  termination_reason: z.string().min(3, 'Укажите причину').max(500),
  generate_act: z.boolean(),
});

type FormData = z.infer<typeof schema>;

interface TerminateContractWizardProps {
  isOpen: boolean;
  onClose: () => void;
  contract: Contract | null;
}

export function TerminateContractWizard({ isOpen, onClose, contract }: TerminateContractWizardProps) {
  const queryClient = useQueryClient();
  const [step, setStep] = useState(1);
  useEscapeKey(onClose);

  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      effective_date: '',
      termination_reason: '',
      generate_act: true,
    },
  });

  const values = watch();

  useEffect(() => {
    if (isOpen && contract) {
      setStep(1);
      reset({
        effective_date: new Date().toISOString().slice(0, 10),
        termination_reason: '',
        generate_act: true,
      });
    }
  }, [isOpen, contract, reset]);

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      contractsApi.terminate(contract!.id, {
        effective_date: data.effective_date,
        termination_reason: data.termination_reason,
        generate_act: data.generate_act,
      }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
      queryClient.invalidateQueries({ queryKey: ['contract', contract?.id] });
      queryClient.invalidateQueries({ queryKey: ['contract-charges', contract?.id] });
      queryClient.invalidateQueries({ queryKey: ['contract-ledger', contract?.id] });
      queryClient.invalidateQueries({ queryKey: ['contract-events', contract?.id] });
      const parts = [
        'Договор расторгнут',
        result.charges_deleted ? `удалено начислений: ${result.charges_deleted}` : null,
        result.charges_updated ? `пересчитано: ${result.charges_updated}` : null,
      ].filter(Boolean);
      toast.success(parts.join(' · '));
      if (result.document_url) {
        window.open(result.document_url, '_blank');
      }
      onClose();
    },
    onError: (error) => showError(error, 'Ошибка расторжения'),
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
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100">
                    <FileX className="h-5 w-5 text-amber-700" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">Расторжение договора</h2>
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
                  <Input
                    label="Дата расторжения"
                    type="date"
                    min={contract.start_date}
                    max={contract.end_date}
                    error={errors.effective_date?.message}
                    {...register('effective_date')}
                  />
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Причина</label>
                    <textarea
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      rows={3}
                      placeholder="Например: соглашение сторон"
                      {...register('termination_reason')}
                    />
                    {errors.termination_reason && (
                      <p className="mt-1 text-sm text-red-600">{errors.termination_reason.message}</p>
                    )}
                  </div>
                  <label className="flex items-center gap-2 text-sm text-gray-700">
                    <input type="checkbox" className="rounded border-gray-300" {...register('generate_act')} />
                    Сформировать акт расторжения (PDF)
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
                      <span className="text-gray-500">Дата</span>
                      <span>{values.effective_date}</span>
                    </div>
                    <div className="flex justify-between gap-4">
                      <span className="text-gray-500 shrink-0">Причина</span>
                      <span className="text-right">{values.termination_reason}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Акт PDF</span>
                      <span>{values.generate_act ? 'Да' : 'Нет'}</span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">
                    Будущие неоплаченные начисления будут удалены, текущий период — пересчитан пропорционально.
                    Статус договора станет «Расторгнут».
                  </p>
                  <div className="flex gap-3 pt-2">
                    <Button variant="secondary" type="button" onClick={() => setStep(1)} className="flex-1">
                      Назад
                    </Button>
                    <Button
                      variant="danger"
                      type="button"
                      onClick={onConfirm}
                      isLoading={mutation.isPending}
                      className="flex-1"
                    >
                      Расторгнуть
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
