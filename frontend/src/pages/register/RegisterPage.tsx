import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { UserPlus } from 'lucide-react';
import { showError, showSuccess } from '@/shared/lib/toast';
import { authApi } from '@/features/auth/api';
import { useAuthStore } from '@/features/auth/store';
import { registerSchema, type RegisterFormData } from '@/features/auth/schema';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { Card } from '@/shared/ui/Card';

export default function RegisterPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [error, setError] = useState('');

  const { register, handleSubmit, formState: { errors } } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const registerMutation = useMutation({
    mutationFn: (data: RegisterFormData) => authApi.register({
      full_name: data.full_name,
      email: data.email,
      password: data.password,
    }),
    onSuccess: async (data) => {
      setAuth(data.user);
      await useAuthStore.getState().fetchUser();
      showSuccess('Аккаунт создан');
      navigate('/dashboard');
    },
    onError: (error) => {
      setError('Не удалось создать аккаунт');
      showError(error, 'Не удалось создать аккаунт');
    },
  });

  const onSubmit = (data: RegisterFormData) => {
    setError('');
    registerMutation.mutate(data);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">Landlords</h1>
          <p className="mt-2 text-gray-600">Создайте аккаунт для управления арендой</p>
        </div>
        <Card>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}
            <Input label="Имя" placeholder="Иван Иванов" error={errors.full_name?.message} {...register('full_name')} />
            <Input label="Email" type="email" placeholder="you@example.com" error={errors.email?.message} {...register('email')} />
            <Input label="Пароль" type="password" placeholder="Не менее 6 символов" error={errors.password?.message} {...register('password')} />
            <Input label="Повторите пароль" type="password" error={errors.confirm?.message} {...register('confirm')} />
            <Button
              type="submit"
              className="w-full"
              isLoading={registerMutation.isPending}
              leftIcon={<UserPlus className="h-4 w-4" />}
            >
              Создать аккаунт
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-gray-600">
            Уже есть аккаунт?{' '}
            <Link to="/login" className="text-blue-600 hover:underline">Войти</Link>
          </p>
        </Card>
        <p className="mt-6 text-center text-xs text-gray-400 space-x-3">
          <a href="/offer" className="hover:text-gray-600 hover:underline">Оферта</a>
          <a href="/privacy" className="hover:text-gray-600 hover:underline">Конфиденциальность</a>
          <a href="/terms" className="hover:text-gray-600 hover:underline">Условия</a>
          <a href="/status" className="hover:text-gray-600 hover:underline">Статус</a>
        </p>
      </motion.div>
    </div>
  );
}
