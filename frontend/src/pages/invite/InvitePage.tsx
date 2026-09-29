import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { UserPlus, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { z } from 'zod';
import { accountApi } from '@/features/account/api';
import { useAuthStore } from '@/features/auth/store';
import { ROLE_LABELS } from '@/entities/account';
import { showError } from '@/shared/lib/toast';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { Card } from '@/shared/ui/Card';
import { FullPageLoader } from '@/shared/ui/FullPageLoader';

const schema = z.object({
  full_name: z.string().min(1, 'Имя обязательно'),
  password: z.string().min(6, 'Минимум 6 символов'),
  confirm: z.string(),
}).refine((d) => d.password === d.confirm, { message: 'Пароли не совпадают', path: ['confirm'] });

export default function InvitePage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [gone, setGone] = useState(false);

  const { data: preview, isLoading, isError } = useQuery({
    queryKey: ['invite-preview', token],
    queryFn: () => accountApi.getInvitePreview(token!),
    enabled: Boolean(token),
    retry: false,
  });

  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
    values: {
      full_name: preview?.full_name || '',
      password: '',
      confirm: '',
    },
  });

  const mutation = useMutation({
    mutationFn: (data: { password: string; full_name: string }) =>
      accountApi.acceptInvite(token!, data),
    onSuccess: async (data) => {
      setAuth(data.user, data.token);
      await useAuthStore.getState().fetchUser();
      toast.success('Добро пожаловать!');
      navigate('/dashboard');
    },
    onError: (error: unknown) => {
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 410) {
        setGone(true);
        return;
      }
      showError(error, 'Не удалось принять приглашение');
    },
  });

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h1 className="text-xl font-bold mb-2">Ссылка недействительна</h1>
          <p className="text-gray-500 mb-4">Токен отсутствует. Попросите новое приглашение.</p>
          <Link to="/login" className="text-blue-600 hover:underline">Войти</Link>
        </div>
      </div>
    );
  }

  if (isLoading) return <FullPageLoader />;

  if (gone || isError || !preview) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="text-center max-w-md">
          <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h1 className="text-xl font-bold mb-2">Приглашение недоступно</h1>
          <p className="text-gray-500 mb-4">
            Ссылка истекла, отозвана или уже использована. Попросите владельца отправить новую.
          </p>
          <Link to="/login" className="text-blue-600 hover:underline">Войти</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">Приглашение</h1>
          <p className="mt-2 text-gray-600">
            Вас пригласили в «{preview.account_name}» как{' '}
            {ROLE_LABELS[preview.role] ?? preview.role}
          </p>
        </div>
        <Card>
          <form
            onSubmit={handleSubmit((d) =>
              mutation.mutate({ password: d.password, full_name: d.full_name })
            )}
            className="space-y-4"
          >
            <Input label="Email" value={preview.email} disabled />
            <Input label="Имя" error={errors.full_name?.message} {...register('full_name')} />
            <Input label="Пароль" type="password" error={errors.password?.message} {...register('password')} />
            <Input label="Подтверждение" type="password" error={errors.confirm?.message} {...register('confirm')} />
            <Button
              type="submit"
              className="w-full"
              isLoading={mutation.isPending}
              leftIcon={<UserPlus className="h-4 w-4" />}
            >
              Принять и войти
            </Button>
          </form>
        </Card>
      </motion.div>
    </div>
  );
}
