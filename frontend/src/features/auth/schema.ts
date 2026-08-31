// frontend/src/features/auth/schema.ts
import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().min(1, 'Email обязателен').email('Неверный формат email'),
  password: z.string().min(1, 'Пароль обязателен').min(6, 'Минимум 6 символов'),
});

export type LoginFormData = z.infer<typeof loginSchema>;