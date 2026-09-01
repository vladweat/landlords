import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { User, Key, Trash2 } from 'lucide-react';
import { authApi } from '@/features/auth/api';
import { useAuthStore } from '@/features/auth/store';
import { showError } from '@/shared/lib/toast';
import { Card } from '@/shared/ui/Card';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { z } from 'zod';

const profileSchema = z.object({
  full_name: z.string().min(1, 'Имя обязательно'),
  phone: z.string().optional(),
});

const passwordSchema = z.object({
  current_password: z.string().min(1, 'Текущий пароль обязателен'),
  new_password: z.string().min(6, 'Минимум 6 символов'),
});

export default function SettingsPage() {
  const navigate = useNavigate();
  const { user, setAuth, logout } = useAuthStore();

  const { register: profileRegister, handleSubmit: handleProfileSubmit, formState: { errors: profileErrors } } = useForm({
    resolver: zodResolver(profileSchema),
    defaultValues: { full_name: user?.full_name || '', phone: user?.phone || '' },
  });

  const { register: passwordRegister, handleSubmit: handlePasswordSubmit, reset: resetPassword, formState: { errors: passwordErrors } } = useForm({
    resolver: zodResolver(passwordSchema),
  });

  const profileMutation = useMutation({
    mutationFn: authApi.updateProfile,
    onSuccess: (data) => {
      if (user) setAuth({
        ...user,
        full_name: data.data.full_name,
        phone: data.data.phone ?? null,
      }, localStorage.getItem('access_token')!);
      toast.success('Профиль обновлён');
    },
    onError: (error) => showError(error, 'Ошибка обновления'),
  });

  const passwordMutation = useMutation({
    mutationFn: authApi.changePassword,
    onSuccess: () => { toast.success('Пароль изменён'); resetPassword(); },
    onError: (error) => showError(error, 'Ошибка смены пароля'),
  });

  const deleteMutation = useMutation({
    mutationFn: authApi.deleteAccount,
    onSuccess: () => { toast.success('Аккаунт удалён'); logout(); navigate('/login'); },
    onError: (error) => showError(error, 'Ошибка удаления'),
  });

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-semibold text-gray-900">Настройки</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <h2 className="text-lg font-medium text-gray-800 mb-4 flex items-center gap-2"><User className="h-5 w-5" /> Профиль</h2>
          <form onSubmit={handleProfileSubmit((d) => profileMutation.mutate(d))} className="space-y-4">
            <Input label="Имя" error={profileErrors.full_name?.message} {...profileRegister('full_name')} />
            <Input label="Телефон" placeholder="+79991234567" error={profileErrors.phone?.message} {...profileRegister('phone')} />
            <Button type="submit" size="sm" isLoading={profileMutation.isPending}>Сохранить</Button>
          </form>
        </Card>

        <Card>
          <h2 className="text-lg font-medium text-gray-800 mb-4 flex items-center gap-2"><Key className="h-5 w-5" /> Пароль</h2>
          <form onSubmit={handlePasswordSubmit((d) => passwordMutation.mutate(d))} className="space-y-4">
            <Input label="Текущий пароль" type="password" error={passwordErrors.current_password?.message} {...passwordRegister('current_password')} />
            <Input label="Новый пароль" type="password" error={passwordErrors.new_password?.message} {...passwordRegister('new_password')} />
            <Button type="submit" size="sm" isLoading={passwordMutation.isPending}>Сменить пароль</Button>
          </form>
        </Card>
      </div>

      <Card className="border-red-200">
        <h2 className="text-lg font-medium text-red-600 mb-2 flex items-center gap-2"><Trash2 className="h-5 w-5" /> Удалить аккаунт</h2>
        <p className="text-sm text-gray-500 mb-4">Все данные будут удалены без возможности восстановления.</p>
        <Button variant="danger" size="sm" onClick={() => { if (confirm('Вы уверены? Это действие необратимо.')) deleteMutation.mutate(); }} isLoading={deleteMutation.isPending}>Удалить аккаунт</Button>
      </Card>
    </div>
  );
}
