import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, ArrowLeft, CheckCircle } from 'lucide-react';
import { authApi } from '@/features/auth/api';
import { showError } from '@/shared/lib/toast';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { Card } from '@/shared/ui/Card';
import { z } from 'zod';

const schema = z.object({ email: z.string().min(1, 'Email обязателен').email('Неверный формат') });

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (data: { email: string }) => authApi.forgotPassword(data.email),
    onSuccess: () => setSent(true),
    onError: (error) => showError(error, 'Ошибка отправки'),
  });

  if (sent) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md text-center">
          <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-gray-900 mb-2">Инструкция отправлена</h1>
          <p className="text-gray-500 mb-6">Если аккаунт с таким email существует, инструкция отправлена на почту. Проверьте папку «Спам».</p>
          <Link to="/login" className="text-blue-600 hover:underline flex items-center justify-center gap-1"><ArrowLeft className="h-4 w-4" /> Вернуться на вход</Link>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">Landlords</h1>
          <p className="mt-2 text-gray-600">Восстановление пароля</p>
        </div>
        <Card>
          <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4">
            <Input label="Email" type="email" placeholder="you@example.com" error={errors.email?.message} {...register('email')} />
            <Button type="submit" className="w-full" isLoading={mutation.isPending} leftIcon={<Mail className="h-4 w-4" />}>Восстановить</Button>
          </form>
          <div className="mt-4 text-center">
            <Link to="/login" className="text-sm text-blue-600 hover:underline flex items-center justify-center gap-1"><ArrowLeft className="h-3 w-3" /> Вернуться на вход</Link>
          </div>
        </Card>
      </motion.div>
    </div>
  );
}
