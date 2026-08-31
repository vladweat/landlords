import { z } from 'zod';

export const tenantSchema = z.object({
  full_name: z.string().min(1, 'Имя обязательно'),
  email: z.string().min(1, 'Email обязателен').email('Неверный формат'),
  phone: z.string().min(1, 'Телефон обязателен'),
});

export type TenantFormData = z.infer<typeof tenantSchema>;
