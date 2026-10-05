import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Bell,
  Building2,
  Download,
  FileText,
  Key,
  LifeBuoy,
  ShieldCheck,
  Trash2,
  User,
  Users,
  type LucideIcon,
} from 'lucide-react';
import { authApi } from '@/features/auth/api';
import { accountApi } from '@/features/account/api';
import { PlanSection } from '@/features/account/components/PlanSection';
import { ContractTemplatesSection } from '@/features/contract-templates/components/ContractTemplatesSection';
import { useAuthStore } from '@/features/auth/store';
import { useCan } from '@/features/auth/permissions';
import { ROLE_LABELS, type Role } from '@/entities/account';
import { showError } from '@/shared/lib/toast';
import { Card } from '@/shared/ui/Card';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
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

const defaultCurrencies = ['RUB', 'USD', 'EUR', 'KZT'];
const defaultTimezones = [
  'Europe/Moscow',
  'Europe/Kaliningrad',
  'Asia/Yekaterinburg',
  'Asia/Novosibirsk',
  'Asia/Vladivostok',
];

const roleHighlights: Record<Role, string[]> = {
  owner: [
    'Управляет тарифом, реквизитами и командой аккаунта.',
    'Редактирует все разделы CRM и может удалить аккаунт.',
    'Отвечает за оплату подписки и доступ участников.',
  ],
  manager: [
    'Работает с объектами, арендаторами, договорами и документами.',
    'Видит общие настройки аккаунта, но не управляет биллингом и командой.',
    'Может выполнять ежедневные операции без доступа к опасным действиям.',
  ],
  accountant: [
    'Работает с платежами, начислениями, расходами и напоминаниями.',
    'Видит настройки аккаунта в справочном режиме без прав управления.',
    'Не управляет командой, биллингом и удалением аккаунта.',
  ],
};

type SectionId = 'personal' | 'account' | 'team' | 'documents';

function Section({
  id,
  title,
  description,
  icon: Icon,
  children,
}: {
  id: SectionId;
  title: string;
  description: string;
  icon: LucideIcon;
  children: ReactNode;
}) {
  return (
    <section id={id} className="space-y-4 scroll-mt-6">
      <div className="flex items-start gap-3">
        <div className="rounded-xl bg-slate-100 p-2 text-slate-600">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <p className="mt-1 text-sm text-gray-500">{description}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

function ReadOnlyField({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3">
      <div className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</div>
      <div className="mt-1 whitespace-pre-wrap text-sm text-gray-900">{value}</div>
      {hint && <div className="mt-1 text-xs text-gray-500">{hint}</div>}
    </div>
  );
}

export default function SettingsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const { user, account, role, setAuth, logout, fetchUser } = useAuthStore();
  const canManageTeam = useCan('manage_team');
  const canManageAccount = useCan('manage_account');
  const [removingUserId, setRemovingUserId] = useState<string | null>(null);
  const [revokingInviteId, setRevokingInviteId] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const billingReturnHandled = useRef(false);

  useEffect(() => {
    if (!canManageAccount || billingReturnHandled.current) return;
    if (searchParams.get('billing') !== 'return') return;
    billingReturnHandled.current = true;

    const paymentId = sessionStorage.getItem('yookassa_payment_id');
    const finish = () => {
      sessionStorage.removeItem('yookassa_payment_id');
      searchParams.delete('billing');
      setSearchParams(searchParams, { replace: true });
    };

    if (!paymentId) {
      finish();
      toast.message('Вернулись из оплаты. Обновите страницу, если тариф не сменился.');
      return;
    }

    void accountApi
      .confirmPayment(paymentId)
      .then(async (result) => {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ['account-subscription'] }),
          fetchUser(),
        ]);
        if (result.status === 'applied') {
          toast.success('Оплата Pro подтверждена');
        } else if (result.status === 'ignored' && result.reason === 'duplicate') {
          toast.success('Подписка Pro уже активна');
        } else {
          toast.message(
            `Платёж ещё не завершён (${result.reason ?? result.status}). Подождите или проверьте ЮKassa.`,
          );
        }
      })
      .catch((error) => showError(error, 'Не удалось подтвердить оплату'))
      .finally(finish);
  }, [canManageAccount, searchParams, setSearchParams, queryClient, fetchUser]);

  const { register: profileRegister, handleSubmit: handleProfileSubmit, formState: { errors: profileErrors } } = useForm({
    resolver: zodResolver(profileSchema),
    values: { full_name: user?.full_name || '', phone: user?.phone || '' },
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

  const { data: subscription } = useQuery({
    queryKey: ['account-subscription'],
    queryFn: accountApi.getSubscription,
  });

  const seatsOccupied =
    (subscription?.usage.users ?? 0) + invites.length;
  const seatsAtLimit =
    !!subscription && seatsOccupied >= subscription.limits.max_users;

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
      queryClient.invalidateQueries({ queryKey: ['account-subscription'] });
      resetInvite();
      let copied = false;
      try {
        await navigator.clipboard.writeText(invite.invite_url);
        copied = true;
      } catch {
        /* clipboard may be unavailable */
      }
      if (invite.email_sent === false) {
        toast.warning(
          copied
            ? 'Приглашение создано, письмо не ушло — ссылка скопирована'
            : 'Приглашение создано, письмо не ушло — скопируйте ссылку из списка',
        );
      } else if (copied) {
        toast.success('Приглашение отправлено, ссылка скопирована');
      } else {
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
    onSuccess: () => {
      setDeleteDialogOpen(false);
      toast.success('Аккаунт удалён');
      logout();
      navigate('/login');
    },
    onError: (error) => showError(error, 'Ошибка удаления'),
  });

  const exportMutation = useMutation({
    mutationFn: accountApi.exportData,
    onSuccess: () => toast.success('Архив с данными скачан'),
    onError: (error) => showError(error, 'Ошибка выгрузки'),
  });

  const currencyOptions = useMemo(() => {
    const current = account?.base_currency?.toUpperCase();
    return Array.from(new Set(current ? [current, ...defaultCurrencies] : defaultCurrencies));
  }, [account?.base_currency]);

  const timezoneOptions = useMemo(() => {
    const current = account?.timezone;
    return Array.from(new Set(current ? [current, ...defaultTimezones] : defaultTimezones));
  }, [account?.timezone]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold text-gray-900">Настройки</h1>
      </div>

      <Section
            id="personal"
            title="Личное"
            description="Профиль, доступ в систему и персональные уведомления."
            icon={User}
          >
            <div className="grid gap-4 xl:grid-cols-2">
              <Card>
                <h3 className="mb-4 flex items-center gap-2 text-lg font-medium text-gray-800">
                  <User className="h-5 w-5" /> Профиль
                </h3>
                <form
                  onSubmit={handleProfileSubmit((d) => profileMutation.mutate(d))}
                  className="space-y-4"
                >
                  <Input
                    label="Email"
                    value={user?.email || ''}
                    disabled
                    className="bg-gray-50 text-gray-500"
                  />
                  <Input
                    label="Имя"
                    error={profileErrors.full_name?.message}
                    {...profileRegister('full_name')}
                  />
                  <Input
                    label="Телефон"
                    placeholder="+79991234567"
                    error={profileErrors.phone?.message}
                    {...profileRegister('phone')}
                  />
                  <Button
                    type="submit"
                    size="sm"
                    isLoading={profileMutation.isPending}
                  >
                    Сохранить
                  </Button>
                </form>
              </Card>

              <Card>
                <h3 className="mb-4 flex items-center gap-2 text-lg font-medium text-gray-800">
                  <Key className="h-5 w-5" /> Пароль
                </h3>
                <form
                  onSubmit={handlePasswordSubmit((d) => passwordMutation.mutate(d))}
                  className="space-y-4"
                >
                  <Input
                    label="Текущий пароль"
                    type="password"
                    error={passwordErrors.current_password?.message}
                    {...passwordRegister('current_password')}
                  />
                  <Input
                    label="Новый пароль"
                    type="password"
                    error={passwordErrors.new_password?.message}
                    {...passwordRegister('new_password')}
                  />
                  <Button
                    type="submit"
                    size="sm"
                    isLoading={passwordMutation.isPending}
                  >
                    Сменить пароль
                  </Button>
                </form>
              </Card>
            </div>

            <Card>
              <h3 className="mb-2 flex items-center gap-2 text-lg font-medium text-gray-800">
                <Bell className="h-5 w-5" /> Уведомления
              </h3>
              <p className="text-sm text-gray-600">
                Следующим шагом здесь можно вынести персональные настройки
                уведомлений: письма о просрочках, завершении договоров и события
                из колокольчика.
              </p>
              <div className="mt-4 rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-500">
                Пока уведомления работают по системным правилам, а этот блок
                оставлен как понятная точка будущего расширения.
              </div>
            </Card>
          </Section>

          <Section
            id="account"
            title="Аккаунт"
            description="Настройки организации, реквизиты для квитанций и тариф."
            icon={Building2}
          >
            {canManageAccount ? (
              <Card>
                <h3 className="mb-4 flex items-center gap-2 text-lg font-medium text-gray-800">
                  <Building2 className="h-5 w-5" /> Организация
                </h3>
                <form
                  onSubmit={handleAccountSubmit((d) => accountMutation.mutate(d))}
                  className="space-y-4"
                >
                  <div className="grid gap-4 xl:grid-cols-2">
                    <Input
                      label="Название аккаунта"
                      error={accountErrors.name?.message}
                      {...accountRegister('name')}
                    />
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">
                        Валюта
                      </label>
                      <select
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        {...accountRegister('base_currency')}
                      >
                        {currencyOptions.map((currency) => (
                          <option key={currency} value={currency}>
                            {currency}
                          </option>
                        ))}
                      </select>
                      {accountErrors.base_currency?.message && (
                        <p className="mt-1 text-sm text-red-600">
                          {accountErrors.base_currency.message}
                        </p>
                      )}
                    </div>
                    <div className="xl:col-span-2">
                      <label className="mb-1 block text-sm font-medium text-gray-700">
                        Часовой пояс
                      </label>
                      <select
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        {...accountRegister('timezone')}
                      >
                        {timezoneOptions.map((timezone) => (
                          <option key={timezone} value={timezone}>
                            {timezone}
                          </option>
                        ))}
                      </select>
                      {accountErrors.timezone?.message && (
                        <p className="mt-1 text-sm text-red-600">
                          {accountErrors.timezone.message}
                        </p>
                      )}
                    </div>
                  </div>

                  <div>
                    <label
                      htmlFor="payment_details"
                      className="mb-1 block text-sm font-medium text-gray-700"
                    >
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

                  <Button
                    type="submit"
                    size="sm"
                    isLoading={accountMutation.isPending}
                  >
                    Сохранить настройки аккаунта
                  </Button>
                </form>
              </Card>
            ) : (
              <Card>
                <h3 className="mb-2 flex items-center gap-2 text-lg font-medium text-gray-800">
                  <Building2 className="h-5 w-5" /> Организация
                </h3>
                <p className="mb-4 text-sm text-gray-500">
                  Эти параметры редактирует владелец аккаунта. Для вашей роли они
                  доступны как справочная информация.
                </p>
                <div className="grid gap-3 xl:grid-cols-2">
                  <ReadOnlyField label="Название аккаунта" value={account?.name || 'Не задано'} />
                  <ReadOnlyField label="Валюта" value={account?.base_currency || 'Не задана'} />
                  <ReadOnlyField label="Часовой пояс" value={account?.timezone || 'Не задан'} />
                  <ReadOnlyField
                    label="Реквизиты для оплаты"
                    value={account?.payment_details?.trim() || 'Реквизиты ещё не заполнены'}
                    hint="Используются в публичной квитанции и PDF."
                  />
                </div>
              </Card>
            )}

            <PlanSection />
          </Section>

          <Section
            id="team"
            title="Команда и роли"
            description="Кто работает в аккаунте и какие действия доступны каждой роли."
            icon={Users}
          >
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
              {canManageTeam ? (
                <Card>
                  <h3 className="mb-4 flex items-center gap-2 text-lg font-medium text-gray-800">
                    <Users className="h-5 w-5" /> Команда
                  </h3>

                  {membersLoading ? (
                    <p className="mb-4 text-sm text-gray-500">Загрузка…</p>
                  ) : (
                    <div className="mb-6 overflow-hidden rounded-xl border border-gray-200">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                            <th className="px-3 py-2 font-medium">Участник</th>
                            <th className="px-3 py-2 font-medium">Роль</th>
                            <th className="w-24 px-3 py-2 font-medium"></th>
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
                      <h4 className="mb-2 text-sm font-medium text-gray-700">
                        Ожидают принятия
                      </h4>
                      {invitesLoading ? (
                        <p className="text-sm text-gray-500">Загрузка…</p>
                      ) : (
                        <div className="overflow-hidden rounded-xl border border-gray-200">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                                <th className="px-3 py-2 font-medium">Email</th>
                                <th className="px-3 py-2 font-medium">Роль</th>
                                <th className="w-28 px-3 py-2 font-medium"></th>
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
                                  <td className="space-x-1 px-3 py-2 text-right">
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

                  <h4 className="mb-3 text-sm font-medium text-gray-700">
                    Пригласить участника
                  </h4>
                  {seatsAtLimit && (
                    <p className="mb-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                      Достигнут лимит пользователей тарифа. Смените тариф или
                      отзовите приглашение.
                    </p>
                  )}
                  <form
                    onSubmit={handleInviteSubmit((d) =>
                      createInviteMutation.mutate({
                        email: d.email,
                        full_name: d.full_name,
                        role: d.role as Exclude<Role, 'owner'>,
                      })
                    )}
                    className="max-w-md space-y-3"
                  >
                    <Input
                      label="Email"
                      error={inviteErrors.email?.message}
                      {...inviteRegister('email')}
                    />
                    <Input
                      label="Имя"
                      error={inviteErrors.full_name?.message}
                      {...inviteRegister('full_name')}
                    />
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">
                        Роль
                      </label>
                      <select
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                        {...inviteRegister('role')}
                      >
                        <option value="manager">{ROLE_LABELS.manager}</option>
                        <option value="accountant">{ROLE_LABELS.accountant}</option>
                      </select>
                    </div>
                    <Button
                      type="submit"
                      size="sm"
                      isLoading={createInviteMutation.isPending}
                      disabled={seatsAtLimit}
                    >
                      Отправить приглашение
                    </Button>
                  </form>
                </Card>
              ) : (
                <Card>
                  <h3 className="mb-2 flex items-center gap-2 text-lg font-medium text-gray-800">
                    <Users className="h-5 w-5" /> Команда
                  </h3>
                  <p className="text-sm text-gray-600">
                    Управление участниками доступно только владельцу аккаунта.
                    Ниже остаётся краткая памятка по ролям, чтобы было понятно,
                    где заканчиваются ваши права.
                  </p>
                </Card>
              )}

              <Card>
                <h3 className="mb-4 flex items-center gap-2 text-lg font-medium text-gray-800">
                  <ShieldCheck className="h-5 w-5" /> Роли и доступ
                </h3>
                <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3">
                  <div className="text-sm font-medium text-blue-900">
                    Ваша роль: {role ? ROLE_LABELS[role] : 'Не определена'}
                  </div>
                  <ul className="mt-3 space-y-2 text-sm text-blue-900">
                    {(role ? roleHighlights[role] : []).map((item) => (
                      <li key={item} className="flex gap-2">
                        <span className="mt-1 h-1.5 w-1.5 rounded-full bg-blue-700" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="mt-4 space-y-3 text-sm text-gray-600">
                  <p>
                    <span className="font-medium text-gray-900">Владелец</span> управляет
                    тарифом, командой и настройками аккаунта.
                  </p>
                  <p>
                    <span className="font-medium text-gray-900">Менеджер</span> работает с
                    объектами, арендаторами, договорами и документами без доступа к
                    биллингу и команде.
                  </p>
                  <p>
                    <span className="font-medium text-gray-900">Бухгалтер</span> ведёт
                    платежи, начисления, расходы и напоминания без доступа к
                    управлению аккаунтом.
                  </p>
                </div>
              </Card>
            </div>
          </Section>

          <Section
            id="documents"
            title="Договоры и данные"
            description="Шаблоны документов, поддержка, экспорт и безопасные действия."
            icon={FileText}
          >
            <ContractTemplatesSection />

            <div className="grid gap-4 xl:grid-cols-2">
              <Card>
                <h3 className="mb-2 flex items-center gap-2 text-lg font-medium text-gray-800">
                  <LifeBuoy className="h-5 w-5" /> Поддержка
                </h3>
                <p className="mb-4 text-sm text-gray-500">
                  Если нужна помощь с аккаунтом, оплатой или настройкой CRM, используйте
                  быстрые точки входа ниже.
                </p>
                <div className="flex flex-wrap gap-3">
                  <a
                    href="mailto:hello@landlords.ru"
                    className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
                  >
                    Написать в поддержку
                  </a>
                  <a
                    href="/status"
                    className="inline-flex items-center rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
                  >
                    Статус сервиса
                  </a>
                </div>
                <div className="mt-4 flex flex-wrap gap-3 text-sm">
                  <a href="/offer" className="text-blue-600 hover:underline">
                    Оферта
                  </a>
                  <a href="/privacy" className="text-blue-600 hover:underline">
                    Конфиденциальность
                  </a>
                  <a href="/terms" className="text-blue-600 hover:underline">
                    Условия
                  </a>
                </div>
              </Card>

              {canManageAccount ? (
                <Card>
                  <h3 className="mb-2 flex items-center gap-2 text-lg font-medium text-gray-800">
                    <Download className="h-5 w-5" /> Мои данные
                  </h3>
                  <p className="mb-4 text-sm text-gray-500">
                    Скачайте архив с данными аккаунта в JSON. Документы в бинарном виде
                    не включаются, только метаданные.
                  </p>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => exportMutation.mutate()}
                    isLoading={exportMutation.isPending}
                    leftIcon={<Download className="h-4 w-4" />}
                  >
                    Скачать мои данные
                  </Button>
                </Card>
              ) : (
                <Card>
                  <h3 className="mb-2 flex items-center gap-2 text-lg font-medium text-gray-800">
                    <Download className="h-5 w-5" /> Данные аккаунта
                  </h3>
                  <p className="text-sm text-gray-500">
                    Выгрузка и удаление аккаунта доступны владельцу. Если вам нужен экспорт,
                    обратитесь к owner.
                  </p>
                </Card>
              )}
            </div>

            {canManageAccount && (
              <Card className="border-red-200 bg-red-50/40">
                <h3 className="mb-2 flex items-center gap-2 text-lg font-medium text-red-700">
                  <Trash2 className="h-5 w-5" /> Опасная зона
                </h3>
                <p className="mb-4 text-sm text-red-700/80">
                  Удаление аккаунта необратимо. Перед этим рекомендуется скачать выгрузку
                  с данными.
                </p>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => setDeleteDialogOpen(true)}
                  isLoading={deleteMutation.isPending}
                >
                  Удалить аккаунт
                </Button>
              </Card>
            )}
      </Section>

      <ConfirmDialog
        isOpen={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        onConfirm={() => deleteMutation.mutate()}
        title="Удалить аккаунт?"
        message="Действие необратимо. Для подтверждения введите DELETE."
        isLoading={deleteMutation.isPending}
        requireTypedConfirmation="DELETE"
        confirmLabel="Удалить навсегда"
      />

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
