import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { User, Key, Trash2, Users, Building2 } from 'lucide-react';
import { authApi } from '@/features/auth/api';
import { accountApi } from '@/features/account/api';
import { ContractTemplatesSection } from '@/features/contract-templates/components/ContractTemplatesSection';
import { useAuthStore } from '@/features/auth/store';
import { useCan } from '@/features/auth/permissions';
import { ROLE_LABELS, type Role } from '@/entities/account';
import { showError } from '@/shared/lib/toast';
import { Card } from '@/shared/ui/Card';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { useState } from 'react';
import { z } from 'zod';

const profileSchema = z.object({
  full_name: z.string().min(1, 'Имя обязательно'),
  phone: z.string().optional(),
});

const passwordSchema = z.object({
  current_password: z.string().min(1, 'Текущий пароль обязателен'),
  new_password: z.string().min(6, 'Минимум 6 символов'),
});

const accountSchema = z.object({
  name: z.string().min(1, 'Название обязательно'),
  base_currency: z.string().length(3, 'Код валюты из 3 символов'),
  timezone: z.string().min(1, 'Часовой пояс обязателен'),
  payment_details: z.string().optional(),
});

const inviteSchema = z.object({
  email: z.string().email('Некорректный email'),
  full_name: z.string().min(1, 'Имя обязательно'),
  role: z.enum(['manager', 'accountant']),
});

export default function SettingsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, account, role, setAuth, logout, fetchUser } = useAuthStore();
  const canManageTeam = useCan('manage_team');
  const canManageAccount = useCan('manage_account');
  const [removingUserId, setRemovingUserId] = useState<string | null>(null);
  const [revokingInviteId, setRevokingInviteId] = useState<string | null>(null);

  const { register: profileRegister, handleSubmit: handleProfileSubmit, formState: { errors: profileErrors } } = useForm({
    resolver: zodResolver(profileSchema),
    defaultValues: { full_name: user?.full_name || '', phone: user?.phone || '' },
  });

  const { register: passwordRegister, handleSubmit: handlePasswordSubmit, reset: resetPassword, formState: { errors: passwordErrors } } = useForm({
    resolver: zodResolver(passwordSchema),
  });

  const { register: accountRegister, handleSubmit: handleAccountSubmit, formState: { errors: accountErrors } } = useForm({
    resolver: zodResolver(accountSchema),
    values: {
      name: account?.name || '',
      base_currency: account?.base_currency || 'RUB',
      timezone: account?.timezone || 'Europe/Moscow',
      payment_details: account?.payment_details || '',
    },
  });

  const { register: inviteRegister, handleSubmit: handleInviteSubmit, reset: resetInvite, formState: { errors: inviteErrors } } = useForm({
    resolver: zodResolver(inviteSchema),
    defaultValues: { email: '', full_name: '', role: 'manager' as const },
  });

  const { data: members = [], isLoading: membersLoading } = useQuery({
    queryKey: ['account-members'],
    queryFn: accountApi.listMembers,
    enabled: canManageTeam,
  });

  const { data: invites = [], isLoading: invitesLoading } = useQuery({
    queryKey: ['account-invites'],
    queryFn: accountApi.listInvites,
    enabled: canManageTeam,
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

  const accountMutation = useMutation({
    mutationFn: accountApi.update,
    onSuccess: async () => {
      await fetchUser();
      toast.success('Настройки аккаунта сохранены');
    },
    onError: (error) => showError(error, 'Ошибка сохранения'),
  });

  const createInviteMutation = useMutation({
    mutationFn: accountApi.createInvite,
    onSuccess: async (invite) => {
      queryClient.invalidateQueries({ queryKey: ['account-invites'] });
      resetInvite();
      try {
        await navigator.clipboard.writeText(invite.invite_url);
        toast.success('Приглашение отправлено, ссылка скопирована');
      } catch {
        toast.success('Приглашение создано');
      }
    },
    onError: (error) => showError(error, 'Ошибка приглашения'),
  });

  const revokeInviteMutation = useMutation({
    mutationFn: accountApi.revokeInvite,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['account-invites'] });
      setRevokingInviteId(null);
      toast.success('Приглашение отозвано');
    },
    onError: (error) => showError(error, 'Ошибка отзыва'),
  });

  const updateRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: 'manager' | 'accountant' }) =>
      accountApi.updateMemberRole(userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['account-members'] });
      toast.success('Роль обновлена');
    },
    onError: (error) => showError(error, 'Ошибка смены роли'),
  });

  const removeMemberMutation = useMutation({
    mutationFn: accountApi.removeMember,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['account-members'] });
      setRemovingUserId(null);
      toast.success('Участник удалён');
    },
    onError: (error) => showError(error, 'Ошибка удаления'),
  });

  const deleteMutation = useMutation({
    mutationFn: authApi.deleteAccount,
    onSuccess: () => { toast.success('Аккаунт удалён'); logout(); navigate('/login'); },
    onError: (error) => showError(error, 'Ошибка удаления'),
  });

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Настройки</h1>
        {role && (
          <p className="mt-1 text-sm text-gray-500">
            Роль: {ROLE_LABELS[role]}{account ? ` · ${account.name}` : ''}
          </p>
        )}
      </div>

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

      {canManageAccount && (
        <Card>
          <h2 className="text-lg font-medium text-gray-800 mb-4 flex items-center gap-2">
            <Building2 className="h-5 w-5" /> Аккаунт
          </h2>
          <form onSubmit={handleAccountSubmit((d) => accountMutation.mutate(d))} className="space-y-4 max-w-md">
            <Input label="Название" error={accountErrors.name?.message} {...accountRegister('name')} />
            <Input label="Валюта" error={accountErrors.base_currency?.message} {...accountRegister('base_currency')} />
            <Input label="Часовой пояс" error={accountErrors.timezone?.message} {...accountRegister('timezone')} />
            <div className="w-full">
              <label htmlFor="payment_details" className="mb-1 block text-sm font-medium text-gray-700">
                Реквизиты для оплаты
              </label>
              <textarea
                id="payment_details"
                rows={4}
                placeholder="Карта, СБП, расчётный счёт — текст для квитанции арендатору"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                {...accountRegister('payment_details')}
              />
              <p className="mt-1 text-xs text-gray-500">
                Показываются на публичной квитанции и в PDF.
              </p>
            </div>
            <Button type="submit" size="sm" isLoading={accountMutation.isPending}>Сохранить</Button>
          </form>
        </Card>
      )}

      <ContractTemplatesSection />

      {canManageTeam && (
        <Card>
          <h2 className="text-lg font-medium text-gray-800 mb-4 flex items-center gap-2">
            <Users className="h-5 w-5" /> Команда
          </h2>

          {membersLoading ? (
            <p className="text-sm text-gray-500 mb-4">Загрузка…</p>
          ) : (
            <div className="mb-6 overflow-hidden rounded-lg border border-gray-100">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                    <th className="px-3 py-2 font-medium">Участник</th>
                    <th className="px-3 py-2 font-medium">Роль</th>
                    <th className="px-3 py-2 font-medium w-24"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {members.map((m) => (
                    <tr key={m.user_id}>
                      <td className="px-3 py-2">
                        <div className="font-medium text-gray-900">{m.full_name}</div>
                        <div className="text-gray-500">{m.email}</div>
                      </td>
                      <td className="px-3 py-2">
                        {m.role === 'owner' ? (
                          ROLE_LABELS.owner
                        ) : (
                          <select
                            className="rounded border border-gray-300 px-2 py-1 text-sm"
                            value={m.role}
                            onChange={(e) =>
                              updateRoleMutation.mutate({
                                userId: m.user_id,
                                role: e.target.value as 'manager' | 'accountant',
                              })
                            }
                          >
                            <option value="manager">{ROLE_LABELS.manager}</option>
                            <option value="accountant">{ROLE_LABELS.accountant}</option>
                          </select>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {m.role !== 'owner' && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setRemovingUserId(m.user_id)}
                          >
                            Удалить
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {(invitesLoading || invites.length > 0) && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Ожидают принятия</h3>
              {invitesLoading ? (
                <p className="text-sm text-gray-500">Загрузка…</p>
              ) : (
                <div className="overflow-hidden rounded-lg border border-gray-100">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                        <th className="px-3 py-2 font-medium">Email</th>
                        <th className="px-3 py-2 font-medium">Роль</th>
                        <th className="px-3 py-2 font-medium w-28"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {invites.map((inv) => (
                        <tr key={inv.id}>
                          <td className="px-3 py-2">
                            <div className="font-medium text-gray-900">{inv.full_name}</div>
                            <div className="text-gray-500">{inv.email}</div>
                          </td>
                          <td className="px-3 py-2">
                            {ROLE_LABELS[inv.role as Exclude<Role, 'owner'>] ?? inv.role}
                          </td>
                          <td className="px-3 py-2 text-right space-x-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={async () => {
                                try {
                                  await navigator.clipboard.writeText(inv.invite_url);
                                  toast.success('Ссылка скопирована');
                                } catch {
                                  toast.error('Не удалось скопировать');
                                }
                              }}
                            >
                              Ссылка
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setRevokingInviteId(inv.id)}
                            >
                              Отозвать
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          <h3 className="text-sm font-medium text-gray-700 mb-3">Пригласить участника</h3>
          <form
            onSubmit={handleInviteSubmit((d) =>
              createInviteMutation.mutate({
                email: d.email,
                full_name: d.full_name,
                role: d.role as Exclude<Role, 'owner'>,
              })
            )}
            className="space-y-3 max-w-md"
          >
            <Input label="Email" error={inviteErrors.email?.message} {...inviteRegister('email')} />
            <Input label="Имя" error={inviteErrors.full_name?.message} {...inviteRegister('full_name')} />
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Роль</label>
              <select
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                {...inviteRegister('role')}
              >
                <option value="manager">{ROLE_LABELS.manager}</option>
                <option value="accountant">{ROLE_LABELS.accountant}</option>
              </select>
            </div>
            <Button type="submit" size="sm" isLoading={createInviteMutation.isPending}>
              Отправить приглашение
            </Button>
          </form>
        </Card>
      )}

      {canManageAccount && (
        <Card className="border-red-200">
          <h2 className="text-lg font-medium text-red-600 mb-2 flex items-center gap-2"><Trash2 className="h-5 w-5" /> Удалить аккаунт</h2>
          <p className="text-sm text-gray-500 mb-4">Все данные будут удалены без возможности восстановления.</p>
          <Button variant="danger" size="sm" onClick={() => { if (confirm('Вы уверены? Это действие необратимо.')) deleteMutation.mutate(); }} isLoading={deleteMutation.isPending}>Удалить аккаунт</Button>
        </Card>
      )}

      <ConfirmDialog
        isOpen={!!removingUserId}
        onClose={() => setRemovingUserId(null)}
        onConfirm={() => removingUserId && removeMemberMutation.mutate(removingUserId)}
        title="Удалить участника?"
        message="Пользователь будет удалён из аккаунта без возможности восстановления."
        isLoading={removeMemberMutation.isPending}
      />

      <ConfirmDialog
        isOpen={!!revokingInviteId}
        onClose={() => setRevokingInviteId(null)}
        onConfirm={() => revokingInviteId && revokeInviteMutation.mutate(revokingInviteId)}
        title="Отозвать приглашение?"
        message="Ссылка перестанет работать."
        isLoading={revokeInviteMutation.isPending}
      />
    </div>
  );
}
