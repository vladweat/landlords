import { z } from 'zod';

export const propertySchema = z.object({
  city: z.string().min(1, 'Город обязателен'),
  street: z.string().min(1, 'Улица обязательна'),
  house: z.string().min(1, 'Дом обязателен'),
  building: z.string().optional(),
  apartment: z.string().optional(),
  type: z.enum(['apartment', 'house', 'commercial']),
  size_m2: z.coerce.number().min(1, 'Площадь должна быть больше 0'),
  purchase_price: z.coerce.number().nullable(),
});

export type PropertyFormData = z.infer<typeof propertySchema>;
