import { z } from 'zod';

const moneyString = z
  .string()
  .refine((v) => v === '' || (!Number.isNaN(Number(v)) && Number(v) >= 0), 'Некорректная сумма');

export const propertySchema = z.object({
  city: z.string().min(1, 'Город обязателен'),
  street: z.string().min(1, 'Улица обязательна'),
  house: z.string().min(1, 'Дом обязателен'),
  building: z.string().optional(),
  apartment: z.string().optional(),
  type: z.enum(['apartment', 'house', 'room', 'commercial']),
  size_m2: z.number().min(1, 'Площадь должна быть больше 0'),
  purchase_price: moneyString.nullable(),
});

export type PropertyFormData = z.infer<typeof propertySchema>;
