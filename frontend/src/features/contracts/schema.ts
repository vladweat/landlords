import { z } from 'zod';

const moneyPositive = z
  .string()
  .min(1, 'Укажите сумму')
  .refine((v) => !Number.isNaN(Number(v)) && Number(v) > 0, 'Сумма должна быть больше 0');

const moneyOptional = z
  .string()
  .nullable()
  .optional()
  .refine((v) => v == null || v === '' || (!Number.isNaN(Number(v)) && Number(v) >= 0), 'Некорректная сумма');

export const contractSchema = z
  .object({
    property_id: z.string().min(1, 'Выберите объект'),
    tenant_id: z.string().min(1, 'Выберите арендатора'),
    rent_amount: moneyPositive,
    currency: z.string().min(1),
    start_date: z.string().min(1, 'Укажите дату начала'),
    end_date: z.string().min(1, 'Укажите дату окончания'),
    payment_day: z.number().min(1).max(28),
    billing_period: z.enum(['monthly', 'quarterly', 'yearly']),
    deposit_amount: moneyOptional,
    auto_generate_charges: z.boolean(),
  })
  .refine((data) => !data.start_date || !data.end_date || data.end_date > data.start_date, {
    message: 'Дата окончания должна быть позже даты начала',
    path: ['end_date'],
  });

export type ContractFormData = z.infer<typeof contractSchema>;
