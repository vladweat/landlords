import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Key, ArrowLeft, CheckCircle, AlertTriangle } from 'lucide-react';
import { authApi } from '@/features/auth/api';
import { showError } from '@/shared/lib/toast';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { Card } from '@/shared/ui/Card';
import { z } from 'zod';

const schema = z.object({
  new_password: z.string().min(6, 'Минимум 6 символов'),
  confirm: z.string(),
}).refine((d) => d.new_password === d.confirm, { message: 'Пароли не совпадают', path: ['confirm'] });

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [done, setDone] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (data: { new_password: string }) => authApi.resetPassword({ token: token!, new_password: data.new_password }),
    onSuccess: () => setDone(true),
    onError: (error) => showError(error, 'Ошибка сброса'),
  });

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h1 className="text-xl font-bold mb-2">Ссылка недействительна</h1>
          <p className="text-gray-500 mb-4">Токен отсутствует. Запросите восстановление заново.</p>
          <Link to="/forgot-password" className="text-blue-600 hover:underline">Восстановить пароль</Link>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center">
          <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
          <h1 className="text-xl font-bold mb-2">Пароль изменён</h1>
          <p className="text-gray-500 mb-4">Сейчас перенаправим на вход.</p>
          <Link to="/login" className="text-blue-600 hover:underline flex items-center justify-center gap-1"><ArrowLeft className="h-4 w-4" /> Войти</Link>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">Новый пароль</h1>
        </div>
        <Card>
          <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4">
            <Input label="Новый пароль" type="password" error={errors.new_password?.message} {...register('new_password')} />
            <Input label="Подтверждение" type="password" error={errors.confirm?.message} {...register('confirm')} />
            <Button type="submit" className="w-full" isLoading={mutation.isPending} leftIcon={<Key className="h-4 w-4" />}>Сохранить пароль</Button>
          </form>
        </Card>
      </motion.div>
    </div>
  );
}
