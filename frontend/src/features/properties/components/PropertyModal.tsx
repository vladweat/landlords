import { scrollToTop } from "@/shared/lib/scrollToTop";
import { useEffect } from 'react';
import { useForm, type Resolver } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { showError, showSuccess } from '@/shared/lib/toast';
import { useEscapeKey } from '@/shared/hooks/useEscapeKey';
import { propertiesApi } from '@/features/properties/api';
import { propertySchema, type PropertyFormData } from '@/features/properties/schema';
import type { Property } from '@/entities/property';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';

interface PropertyModalProps { isOpen: boolean; onClose: () => void; property: Property | null; }

export function PropertyModal({ isOpen, onClose, property }: PropertyModalProps) {
  const queryClient = useQueryClient();
  useEscapeKey(onClose);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<PropertyFormData>({
    resolver: zodResolver(propertySchema) as Resolver<PropertyFormData>,
    defaultValues: { city: '', street: '', house: '', building: '', apartment: '', type: 'apartment', size_m2: 0, purchase_price: null },
  });

  useEffect(() => {
    reset(property ? {
      city: property.city || '',
      street: property.street || '',
      house: property.house || '',
      building: property.building || '',
      apartment: property.apartment || '',
      type: property.type,
      size_m2: property.size_m2,
      purchase_price: property.purchase_price ?? null,
    } : { city: '', street: '', house: '', building: '', apartment: '', type: 'apartment', size_m2: 0, purchase_price: null });
  }, [property, reset]);

  const createMutation = useMutation({
    mutationFn: propertiesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['properties'] });
      queryClient.invalidateQueries({ queryKey: ['account-subscription'] });
      scrollToTop();
      showSuccess("Объект добавлен");
      onClose();
    },
    onError: (error) => showError(error, 'Ошибка создания'),
  });

  const updateMutation = useMutation({
    mutationFn: (data: PropertyFormData) => property ? propertiesApi.update(property.id, data) : Promise.reject(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['properties'] });
      if (property) queryClient.invalidateQueries({ queryKey: ['property', property.id] });
      showSuccess('Объект обновлён');
      onClose();
    },
    onError: (error) => showError(error, 'Ошибка обновления'),
  });

  const onSubmit = (data: PropertyFormData) => {
    const payload = {
      ...data,
      purchase_price: data.purchase_price && data.purchase_price !== '' ? data.purchase_price : null,
    };
    property ? updateMutation.mutate(payload) : createMutation.mutate(payload);
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
                <h2 className="text-lg font-semibold text-gray-900">{property ? 'Редактировать объект' : 'Новый объект'}</h2>
                <button onClick={onClose} className="rounded-lg p-1 text-gray-400 hover:bg-gray-100"><X className="h-5 w-5" /></button>
              </div>
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <Input label="Город" placeholder="Москва" error={errors.city?.message} {...register('city')} />
                  <Input label="Улица" placeholder="Тверская" error={errors.street?.message} {...register('street')} />
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <Input label="Дом" placeholder="1" error={errors.house?.message} {...register('house')} />
                  <Input label="Корпус" placeholder="2" error={errors.building?.message} {...register('building')} />
                  <Input label="Квартира" placeholder="10" error={errors.apartment?.message} {...register('apartment')} />
                </div>
                <div className="w-full">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Тип</label>
                  <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" {...register('type')}>
                    <option value="apartment">Квартира</option>
                    <option value="house">Дом</option>
                    <option value="room">Комната</option>
                    <option value="commercial">Коммерция</option>
                  </select>
                </div>
                <Input label="Площадь (м²)" type="number" placeholder="0" error={errors.size_m2?.message} {...register('size_m2', { valueAsNumber: true })} />
                <Input label="Цена покупки" type="number" placeholder="Необязательно" error={errors.purchase_price?.message} {...register('purchase_price')} />
                <div className="flex gap-3 pt-2">
                  <Button type="button" variant="secondary" onClick={onClose} className="flex-1">Отмена</Button>
                  <Button type="submit" className="flex-1" isLoading={isPending}>{property ? 'Сохранить' : 'Добавить'}</Button>
                </div>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
