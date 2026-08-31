import { scrollToTop } from "@/shared/lib/scrollToTop";
import { useEscapeKey } from '@/shared/hooks/useEscapeKey';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { toast } from 'sonner';
import { showError } from '@/shared/lib/toast';
import { tenantsApi } from '@/features/tenants/api';
import { tenantSchema, type TenantFormData } from '@/features/tenants/schema';
import type { Tenant } from '@/entities/tenant';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';

interface TenantModalProps { isOpen: boolean; onClose: () => void; tenant: Tenant | null; }

export function TenantModal({ isOpen, onClose, tenant }: TenantModalProps) {
  useEscapeKey(onClose);
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset, formState: { errors } } = useForm<TenantFormData>({
    resolver: zodResolver(tenantSchema), defaultValues: { full_name: '', email: '', phone: '' },
  });

  useEffect(() => {
    reset(tenant ? { full_name: tenant.full_name, email: tenant.email, phone: tenant.phone } : { full_name: '', email: '', phone: '' });
  }, [tenant, reset]);

  const createMutation = useMutation({
    mutationFn: tenantsApi.create,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['tenants'] }); scrollToTop(); toast.success("Арендатор добавлен"); onClose(); },
    onError: (error) => showError(error, 'Ошибка создания'),
  });

  const updateMutation = useMutation({
    mutationFn: (data: TenantFormData) => tenant ? tenantsApi.update(tenant.id, data) : Promise.reject(),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['tenants'] }); toast.success('Арендатор обновлён'); onClose(); },
    onError: (error) => showError(error, 'Ошибка обновления'),
  });

  const onSubmit = (data: TenantFormData) => { tenant ? updateMutation.mutate(data) : createMutation.mutate(data); };
  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 bg-black/50" onClick={onClose} />
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl max-h-[80vh] overflow-y-auto [scrollbar-width:none] [-ms-overflow-style:none] [rounded-xl bg-white p-6 shadow-xl::-webkit-scrollbar]:hidden">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">{tenant ? 'Редактировать арендатора' : 'Новый арендатор'}</h2>
                <button onClick={onClose} className="rounded-lg p-1 text-gray-400 hover:bg-gray-100"><X className="h-5 w-5" /></button>
              </div>
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <Input autoFocus label="Полное имя" placeholder="Иван Иванов" error={errors.full_name?.message} {...register('full_name')} />
                <Input label="Email" type="email" placeholder="ivan@example.com" error={errors.email?.message} {...register('email')} />
                <Input label="Телефон" placeholder="+7 999 123-45-67" error={errors.phone?.message} {...register('phone')} />
                <div className="flex gap-3 pt-2">
                  <Button type="button" variant="secondary" onClick={onClose} className="flex-1">Отмена</Button>
                  <Button type="submit" className="flex-1" isLoading={isPending}>{tenant ? 'Сохранить' : 'Добавить'}</Button>
                </div>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
