import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CreditCard } from 'lucide-react';
import { toast } from 'sonner';
import { accountApi } from '@/features/account/api';
import { useCan } from '@/features/auth/permissions';
import { useAuthStore } from '@/features/auth/store';
import type { PlanCatalogItem, PlanId, Subscription } from '@/entities/account';
import { showError, showSuccess } from '@/shared/lib/toast';
import { Card } from '@/shared/ui/Card';
import { Button } from '@/shared/ui/Button';

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} ГБ`;
}

function formatPrice(rub: number | null | undefined): string | null {
  if (rub == null) return null;
  return `${rub.toLocaleString('ru-RU')} ₽/мес`;
}

function formatPeriodEnd(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString('ru-RU');
}

function statusLabel(status: string): string {
  switch (status) {
    case 'active':
      return 'Активна';
    case 'past_due':
      return 'Просрочена оплата';
    case 'canceled':
      return 'Отменена';
    default:
      return 'Нет подписки';
  }
}

function UsageBar({
  label,
  used,
  max,
  formatValue,
}: {
  label: string;
  used: number;
  max: number;
  formatValue?: (n: number) => string;
}) {
  const pct = max > 0 ? Math.min(100, Math.round((used / max) * 100)) : 0;
  const fmt = formatValue ?? ((n: number) => String(n));
  const over = used > max;
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="text-gray-600">{label}</span>
        <span className={over ? 'text-red-600' : 'text-gray-800'}>
          {fmt(used)} / {fmt(max)}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-gray-100">
        <div
          className={`h-full rounded-full transition-all ${over ? 'bg-red-500' : 'bg-blue-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function planDescription(item: PlanCatalogItem): string {
  const base = `${item.max_properties} объектов · ${item.max_users} пользователей · ${formatBytes(item.max_storage_bytes)}`;
  const price = formatPrice(item.price_rub_monthly);
  return price ? `${base} · ${price}` : base;
}

function planActionLabel(
  item: PlanCatalogItem,
  subscription: Subscription,
  isCurrent: boolean,
): string {
  if (isCurrent) return 'Текущий';
  if (item.id === 'pro') {
    if (subscription.plan === 'pro' && subscription.subscription_status === 'past_due') {
      return 'Оплатить снова';
    }
    return subscription.billing_enabled ? 'Оплатить Pro' : 'Pro недоступен в демо';
  }
  if (item.id === 'free' && subscription.plan === 'pro') {
    return 'Отменить подписку';
  }
  return 'Выбрать';
}

export function PlanSection() {
  const queryClient = useQueryClient();
  const canManageAccount = useCan('manage_account');
  const fetchUser = useAuthStore((s) => s.fetchUser);

  const { data: subscription, isLoading } = useQuery({
    queryKey: ['account-subscription'],
    queryFn: accountApi.getSubscription,
  });

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['account-subscription'] }),
      fetchUser(),
    ]);
  };

  const changePlanMutation = useMutation({
    mutationFn: (plan: PlanId | string) => accountApi.changePlan(plan),
    onSuccess: async () => {
      await refresh();
      showSuccess('Тариф изменён');
    },
    onError: (error) => showError(error, 'Ошибка смены тарифа'),
  });

  const checkoutMutation = useMutation({
    mutationFn: () => accountApi.createCheckout(),
    onSuccess: (data) => {
      sessionStorage.setItem('yookassa_payment_id', data.payment_id);
      window.location.href = data.confirmation_url;
    },
    onError: (error) => showError(error, 'Не удалось создать оплату'),
  });

  const cancelMutation = useMutation({
    mutationFn: () => accountApi.cancelSubscription(),
    onSuccess: async () => {
      await refresh();
      showSuccess('Подписка отменена');
    },
    onError: (error) => showError(error, 'Не удалось отменить подписку'),
  });

  const pending =
    changePlanMutation.isPending || checkoutMutation.isPending || cancelMutation.isPending;

  const onSelectPlan = (item: PlanCatalogItem) => {
    if (!subscription) return;
    if (item.id === subscription.plan && item.id !== 'pro') return;

    if (item.id === 'pro') {
      if (!subscription.billing_enabled) {
        toast.error('Pro недоступен в демо — онлайн-оплата не подключена.');
        return;
      }
      checkoutMutation.mutate();
      return;
    }

    if (item.id === 'free' && subscription.plan === 'pro') {
      cancelMutation.mutate();
      return;
    }

    changePlanMutation.mutate(item.id);
  };

  const periodLabel = formatPeriodEnd(subscription?.subscription_period_end);

  return (
    <Card>
      <h2 className="mb-1 flex items-center gap-2 text-lg font-medium text-gray-800">
        <CreditCard className="h-5 w-5" /> Тариф и лимиты
      </h2>
      <p className="mb-4 text-sm text-gray-500">
        Здесь видно текущий план, лимиты по аккаунту и доступные действия по подписке.
      </p>

      {isLoading || !subscription ? (
        <p className="text-sm text-gray-500">Загрузка…</p>
      ) : (
        <div className="space-y-5">
          {(subscription.write_blocked || subscription.subscription_status === 'past_due') && (
            <div className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              {subscription.write_blocked
                ? 'Подписка не оплачена: изменения в данных недоступны. Оплатите Pro ниже.'
                : 'Оплата Pro просрочена. Продлите подписку, чтобы сохранить доступ к тарифу.'}
            </div>
          )}

          <div>
            <p className="mb-1 text-sm text-gray-700">
              Текущий план:{' '}
              <span className="font-medium text-gray-900">{subscription.plan_name}</span>
            </p>
            <p className="mb-3 text-xs text-gray-500">
              Подписка: {statusLabel(subscription.subscription_status)}
              {periodLabel ? ` · до ${periodLabel}` : ''}
              {!subscription.billing_enabled ? ' · Pro недоступен в демо' : ''}
            </p>
            <div className="space-y-3">
              <UsageBar
                label="Объекты"
                used={subscription.usage.properties}
                max={subscription.limits.max_properties}
              />
              <UsageBar
                label="Пользователи"
                used={subscription.usage.users}
                max={subscription.limits.max_users}
              />
              <UsageBar
                label="Хранилище"
                used={subscription.usage.storage_bytes}
                max={subscription.limits.max_storage_bytes}
                formatValue={formatBytes}
              />
            </div>
          </div>

          {canManageAccount && (
            <div>
              <div className="mb-3 flex items-center justify-between gap-3">
                <h3 className="text-sm font-medium text-gray-800">Доступные планы</h3>
                {!subscription.billing_enabled && (
                  <span className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-600">
                    Pro недоступен в демо
                  </span>
                )}
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                {subscription.plans_catalog.map((item) => {
                  const isCurrent = item.id === subscription.plan;
                  const label = planActionLabel(item, subscription, isCurrent);
                  const isProAction =
                    item.id === 'pro' &&
                    (!isCurrent || subscription.subscription_status === 'past_due');
                  const disabled =
                    (isCurrent && item.id !== 'pro') ||
                    (isCurrent &&
                      item.id === 'pro' &&
                      subscription.subscription_status === 'active') ||
                    pending ||
                    (item.id === 'pro' && !subscription.billing_enabled && isProAction);

                  return (
                    <div
                      key={item.id}
                      className={`rounded-lg border p-3 ${
                        isCurrent ? 'border-blue-400 bg-blue-50/50' : 'border-gray-200'
                      }`}
                    >
                      <div className="mb-1 font-medium text-gray-900">{item.name}</div>
                      <p className="mb-3 text-xs text-gray-500">{planDescription(item)}</p>
                      <Button
                        size="sm"
                        variant={isCurrent && !isProAction ? 'secondary' : 'primary'}
                        disabled={disabled}
                        isLoading={
                          (checkoutMutation.isPending && item.id === 'pro') ||
                          (cancelMutation.isPending && item.id === 'free') ||
                          (changePlanMutation.isPending &&
                            changePlanMutation.variables === item.id)
                        }
                        onClick={() => onSelectPlan(item)}
                      >
                        {label}
                      </Button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {!canManageAccount && (
            <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-600">
              Изменение тарифа и оплата доступны владельцу аккаунта.
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
