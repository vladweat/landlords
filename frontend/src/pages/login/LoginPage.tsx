import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate, Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { LogIn } from 'lucide-react';
import { showError, showSuccess } from '@/shared/lib/toast';
import { authApi } from '@/features/auth/api';
import { useAuthStore } from '@/features/auth/store';
import { loginSchema, type LoginFormData } from '@/features/auth/schema';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { Card } from '@/shared/ui/Card';

export default function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [error, setError] = useState('');

  const { register, handleSubmit, formState: { errors } } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const loginMutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: async (data) => {
      setAuth(data.user);
      await useAuthStore.getState().fetchUser();
      showSuccess('Вход выполнен');
      navigate('/dashboard');
    },
    onError: (error) => {
      setError('Неверный email или пароль');
      showError(error, 'Неверный email или пароль');
    },
  });

  const onSubmit = (data: LoginFormData) => {
    setError('');
    loginMutation.mutate(data);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">Landlords</h1>
          <p className="mt-2 text-gray-600">Войдите в аккаунт для управления арендой</p>
        </div>
        <Card>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}
            <Input label="Email" type="email" placeholder="you@example.com" error={errors.email?.message} {...register('email')} />
            <Input label="Пароль" type="password" placeholder="Введите пароль" error={errors.password?.message} {...register('password')} />
            <Button type="submit" className="w-full" isLoading={loginMutation.isPending} leftIcon={<LogIn className="h-4 w-4" />}>Войти</Button>
          </form>
          <div className="text-center mt-3">
            <Link to="/forgot-password" className="text-sm text-blue-600 hover:underline">Забыли пароль?</Link>
          </div>
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
