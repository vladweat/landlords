// frontend/src/features/auth/schema.ts
import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().min(1, 'Email обязателен').email('Неверный формат email'),
  password: z.string().min(1, 'Пароль обязателен').min(6, 'Минимум 6 символов'),
});

export type LoginFormData = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
  full_name: z.string().trim().min(1, 'Имя обязательно'),
  email: z.string().trim().min(1, 'Email обязателен').email('Неверный формат email'),
  password: z.string().min(6, 'Минимум 6 символов'),
  confirm: z.string().min(1, 'Повторите пароль'),
}).refine((data) => data.password === data.confirm, {
  message: 'Пароли не совпадают',
  path: ['confirm'],
});

export type RegisterFormData = z.infer<typeof registerSchema>;
