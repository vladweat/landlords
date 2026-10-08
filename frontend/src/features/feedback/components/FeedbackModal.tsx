import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { feedbackApi } from '@/features/feedback/api';
import { showError, showSuccess } from '@/shared/lib/toast';
import { useEscapeKey } from '@/shared/hooks/useEscapeKey';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { z } from 'zod';

const schema = z.object({
  category: z.enum(['bug', 'feature', 'question', 'other']),
  message: z.string().min(10, 'Минимум 10 символов'),
});

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function FeedbackModal({ isOpen, onClose }: FeedbackModalProps) {
  useEscapeKey(onClose);

  const { register, handleSubmit, reset, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { category: 'bug' as const, message: '' },
  });

  const mutation = useMutation({
    mutationFn: feedbackApi.send,
    onSuccess: () => { showSuccess('Спасибо! Мы получили ваше сообщение.'); reset(); onClose(); },
    onError: (error) => showError(error, 'Ошибка отправки'),
  });

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 bg-black/50" onClick={onClose} />
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Обратная связь</h2>
                <button onClick={onClose} className="rounded-lg p-1 text-gray-400 hover:bg-gray-100"><X className="h-5 w-5" /></button>
              </div>
              <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4">
                <div className="w-full">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Тема</label>
                  <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" {...register('category')}>
                    <option value="bug">Ошибка</option>
                    <option value="feature">Предложение</option>
                    <option value="question">Вопрос</option>
                    <option value="other">Другое</option>
                  </select>
                </div>
                <Input label="Сообщение" placeholder="Опишите проблему или предложение..." error={errors.message?.message} {...register('message')} />
                <div className="flex gap-3 pt-2">
                  <Button type="button" variant="secondary" onClick={onClose} className="flex-1">Отмена</Button>
                  <Button type="submit" className="flex-1" isLoading={mutation.isPending}>Отправить</Button>
                </div>
                <p className="text-xs text-gray-400 text-center pt-1">
                  Или напишите на{' '}
                  <a href="mailto:hello@landlords.ru" className="text-blue-600 hover:underline">hello@landlords.ru</a>
                  {' · '}
                  <a href="/status" className="text-blue-600 hover:underline">Статус сервиса</a>
                </p>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
