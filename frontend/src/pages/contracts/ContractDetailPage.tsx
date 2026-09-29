import { useParams, useNavigate, Link } from 'react-router-dom';
import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  FileDown,
  FileText,
  FileX,
  Link2,
  Phone,
  Play,
  RefreshCw,
  Wallet,
  CalendarPlus,
} from 'lucide-react';
import { toast } from 'sonner';
import { showError } from '@/shared/lib/toast';
import { apiClient } from '@/shared/api/client';
import { contractsApi } from '@/features/contracts/api';
import { propertiesApi } from '@/features/properties/api';
import { tenantsApi } from '@/features/tenants/api';
import { paymentsApi } from '@/features/payments/api';
import { portalApi } from '@/features/portal/api';
import { useCan } from '@/features/auth/permissions';
import { Card } from '@/shared/ui/Card';
import { Button } from '@/shared/ui/Button';
import { Skeleton, LedgerSkeleton } from '@/shared/ui/Skeleton';
import { EmptyState } from '@/shared/ui/EmptyState';
import { ActionMenu } from '@/shared/ui/ActionMenu';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { LedgerTable } from '@/features/contracts/components/LedgerTable';
import { ChargePeriodsList, type ChargeRow } from '@/features/contracts/components/ChargePeriodsList';
import { TerminateContractWizard } from '@/features/contracts/components/TerminateContractWizard';
import { AttachmentsSection } from '@/features/documents/components/AttachmentsSection';
import { RenewContractWizard } from '@/features/contracts/components/RenewContractWizard';
import { ContractTimeline } from '@/features/contracts/components/ContractTimeline';
import { PaymentModal } from '@/pages/payments/PaymentModal';
import { copyToClipboard } from '@/shared/lib/clipboard';
import { formatDate, parseLocalDate } from '@/shared/lib/utils';

type TabId = 'periods' | 'ledger' | 'events';

const statusLabels: Record<string, string> = {
  draft: 'Черновик',
  active: 'Активен',
  ended: 'Завершён',
  overdue: 'Просрочен',
  terminated: 'Расторгнут',
};

const statusDots: Record<string, string> = {
  draft: 'bg-gray-400',
  active: 'bg-emerald-500',
  ended: 'bg-blue-500',
  overdue: 'bg-red-500',
  terminated: 'bg-amber-500',
};

const UNPAID = new Set(['pending', 'overdue', 'partially_paid']);

function money(value: number | string, currency: string): string {
  const n = typeof value === 'string' ? Number(value) : value;
  const suffix = currency === 'RUB' ? '₽' : currency;
  return `${n.toLocaleString('ru-RU')} ${suffix}`;
}

function chargeRemaining(c: ChargeRow): number {
  return Math.max(0, Number(c.amount) - Number(c.amount_paid || 0));
}

function daysUntil(dateStr: string): number {
  const target = parseLocalDate(dateStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

function daysLeftLabel(endDate: string): string | null {
  const days = daysUntil(endDate);
  if (days < 0) return `завершён ${Math.abs(days)} дн. назад`;
  if (days === 0) return 'заканчивается сегодня';
  if (days === 1) return 'остался 1 день';
  if (days < 5) return `осталось ${days} дня`;
  return `осталось ${days} дн.`;
}

export default function ContractDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const canWriteContracts = useCan('write_contracts');
  const canWritePayments = useCan('write_payments');
  const canWriteCharges = useCan('write_charges');
  const [terminateOpen, setTerminateOpen] = useState(false);
  const [renewOpen, setRenewOpen] = useState(false);
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [paymentChargeId, setPaymentChargeId] = useState<string | undefined>();
  const [activateOpen, setActivateOpen] = useState(false);
  const [showPaid, setShowPaid] = useState(false);
  const [tab, setTab] = useState<TabId>('periods');

  const { data: contract, isLoading: contractLoading } = useQuery({
    queryKey: ['contract', id],
    queryFn: () => contractsApi.getById(id!),
    enabled: !!id,
  });
  const { data: propertiesData, isLoading: propsLoading } = useQuery({
    queryKey: ['properties'],
    queryFn: () => propertiesApi.getAll({ per_page: 100 }),
  });
  const { data: tenantsData, isLoading: tenantsLoading } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantsApi.getAll({ per_page: 100 }),
  });
  const { data: ledger } = useQuery({
    queryKey: ['contract-ledger', id],
    queryFn: () => contractsApi.getLedger(id!),
    enabled: !!id,
  });
  const { data: charges } = useQuery({
    queryKey: ['contract-charges', id],
    queryFn: () => paymentsApi.getCharges(id!),
    enabled: !!id,
  });
  const { data: pendingClaims } = useQuery({
    queryKey: ['contract-claims', id, 'pending'],
    queryFn: () => portalApi.listClaims(id!, 'pending'),
    enabled: !!id,
  });

  const activateMutation = useMutation({
    mutationFn: () => contractsApi.update(id!, { status: 'active' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract', id] });
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
      queryClient.invalidateQueries({ queryKey: ['contract-charges', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-ledger', id] });
      setActivateOpen(false);
      toast.success('Договор активирован');
      if (contract?.auto_generate_charges) {
        toast.message('Начисления создаются в фоне…');
        const delays = [800, 2000, 4000];
        delays.forEach((ms) => {
          setTimeout(() => {
            queryClient.invalidateQueries({ queryKey: ['contract-charges', id] });
            queryClient.invalidateQueries({ queryKey: ['contract-ledger', id] });
          }, ms);
        });
      }
    },
    onError: (error) => showError(error, 'Не удалось активировать'),
  });

  const generateMutation = useMutation({
    mutationFn: () => contractsApi.generateCharges(id!),
    onSuccess: () => {
      toast.success('Генерация начислений запущена');
      const delays = [800, 2000, 4000];
      delays.forEach((ms) => {
        setTimeout(() => {
          queryClient.invalidateQueries({ queryKey: ['contract-charges', id] });
          queryClient.invalidateQueries({ queryKey: ['contract-ledger', id] });
        }, ms);
      });
    },
    onError: (error) => showError(error, 'Не удалось запустить генерацию'),
  });

  const copyPortalMutation = useMutation({
    mutationFn: () => portalApi.ensureLink(id!),
    onSuccess: async (data) => {
      await copyToClipboard(data.share_url);
    },
    onError: (error) => showError(error, 'Не удалось получить ссылку'),
  });

  const dismissClaimMutation = useMutation({
    mutationFn: (claimId: string) => portalApi.dismissClaim(claimId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract-claims', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-events', id] });
      toast.success('Заявка отклонена');
    },
    onError: (error) => showError(error, 'Не удалось отклонить заявку'),
  });

  const confirmClaimMutation = useMutation({
    mutationFn: (claimId: string) => portalApi.confirmClaim(claimId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract-claims', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-events', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-ledger', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-charges', id] });
      queryClient.invalidateQueries({ queryKey: ['payments'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      toast.success('Платёж проведён');
    },
    onError: (error) => showError(error, 'Не удалось подтвердить оплату'),
  });

  const isLoading = contractLoading || propsLoading || tenantsLoading;

  const chargeList = (charges || []) as ChargeRow[];
  const { openCharges, paidCharges, nextOpen } = useMemo(() => {
    const open = chargeList
      .filter((c) => UNPAID.has(c.status))
      .sort((a, b) => a.due_date.localeCompare(b.due_date));
    const paid = chargeList
      .filter((c) => c.status === 'paid')
      .sort((a, b) => b.due_date.localeCompare(a.due_date));
    return { openCharges: open, paidCharges: paid, nextOpen: open[0] || null };
  }, [chargeList]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-6 w-32" />
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-9 w-40" />
        </div>
        <Card>
          <Skeleton className="h-10 w-48 mb-3" />
          <Skeleton className="h-4 w-72" />
        </Card>
      </div>
    );
  }

  if (!contract) return <p className="text-red-500">Договор не найден</p>;

  const properties = propertiesData?.items || [];
  const tenants = tenantsData?.items || [];
  const property = properties.find((p) => p.id === contract.property_id);
  const tenant = tenants.find((t) => t.id === contract.tenant_id);
  const canTerminate = contract.status === 'draft' || contract.status === 'active' || contract.status === 'overdue';
  const canRenew = contract.status === 'active' || contract.status === 'overdue' || contract.status === 'ended';
  const canPay = contract.status === 'active' || contract.status === 'overdue' || contract.status === 'draft';
  const outstanding = Number(ledger?.outstanding_balance || 0);
  const endLabel = daysLeftLabel(contract.end_date);
  const deposit = contract.deposit_amount && Number(contract.deposit_amount) > 0
    ? Number(contract.deposit_amount)
    : null;

  const openPayment = (chargeId?: string) => {
    setPaymentChargeId(chargeId);
    setPaymentOpen(true);
  };

  const refreshAll = async () => {
    try {
      await contractsApi.refreshStatus(contract.id);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['contract', id] }),
        queryClient.invalidateQueries({ queryKey: ['contract-charges', id] }),
        queryClient.invalidateQueries({ queryKey: ['contract-ledger', id] }),
        queryClient.invalidateQueries({ queryKey: ['contract-events', id] }),
        queryClient.invalidateQueries({ queryKey: ['contract-claims', id] }),
        queryClient.invalidateQueries({ queryKey: ['contracts'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] }),
      ]);
      toast.success('Данные обновлены');
    } catch (error) {
      showError(error, 'Не удалось обновить');
    }
  };

  const tabs: { id: TabId; label: string }[] = [
    { id: 'periods', label: 'Периоды' },
    { id: 'ledger', label: 'Касса' },
    { id: 'events', label: 'События' },
  ];

  const menuItems = [
    ...(contract.status === 'draft'
      ? [{ label: 'Активировать', icon: <Play className="h-4 w-4" />, onClick: () => setActivateOpen(true) }]
      : []),
    ...((contract.status === 'active' || contract.status === 'overdue') && chargeList.length === 0 && canWriteCharges
      ? [{
          label: generateMutation.isPending ? 'Генерация…' : 'Сгенерировать начисления',
          icon: <CalendarPlus className="h-4 w-4" />,
          onClick: () => generateMutation.mutate(),
        }]
      : []),
    ...(canRenew
      ? [{ label: 'Продлить', icon: <RefreshCw className="h-4 w-4" />, onClick: () => setRenewOpen(true) }]
      : []),
    {
      label: 'Скачать PDF',
      icon: <FileDown className="h-4 w-4" />,
      onClick: async () => {
        try {
          const res = await apiClient.get<{ status: string; data: { url: string } }>(
            `/contracts/${contract.id}/document`,
          );
          const token = localStorage.getItem('access_token');
          const fileRes = await fetch(res.data.data.url, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          });
          if (!fileRes.ok) throw new Error('download failed');
          const blob = await fileRes.blob();
          const objectUrl = URL.createObjectURL(blob);
          window.open(objectUrl, '_blank');
          setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
          queryClient.invalidateQueries({ queryKey: ['contract-documents', contract.id] });
        } catch (error) {
          showError(error, 'Ошибка скачивания');
        }
      },
    },
    {
      label: 'Копировать ID',
      icon: <FileText className="h-4 w-4" />,
      onClick: () => copyToClipboard(contract.id),
    },
    ...(canWriteContracts
      ? [{
          label: copyPortalMutation.isPending ? 'Ссылка…' : 'Ссылка для арендатора',
          icon: <Link2 className="h-4 w-4" />,
          onClick: () => copyPortalMutation.mutate(),
        }]
      : []),
    ...(canTerminate
      ? [{ label: 'Расторгнуть', icon: <FileX className="h-4 w-4" />, danger: true, onClick: () => setTerminateOpen(true) }]
      : []),
  ];

  const pendingClaim = pendingClaims?.[0] ?? null;

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate('/contracts')}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900"
      >
        <ArrowLeft className="h-4 w-4" /> Назад
      </button>

      {pendingClaim && (
        <div className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="text-sm font-medium text-teal-900">Арендатор сообщил об оплате</p>
              <p className="mt-0.5 text-sm text-teal-800">
                {pendingClaim.amount
                  ? money(pendingClaim.amount, contract.currency)
                  : 'Сумма не указана'}
                {pendingClaim.note ? ` · ${pendingClaim.note}` : ''}
              </p>
            </div>
            {canWritePayments && (
              <div className="flex flex-wrap gap-2 shrink-0">
                <Button
                  size="sm"
                  variant="secondary"
                  isLoading={dismissClaimMutation.isPending}
                  onClick={() => dismissClaimMutation.mutate(pendingClaim.id)}
                >
                  Отклонить
                </Button>
                <Button
                  size="sm"
                  isLoading={confirmClaimMutation.isPending}
                  onClick={() => confirmClaimMutation.mutate(pendingClaim.id)}
                >
                  Подтвердить платёж
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Шапка */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 space-y-2">
          <h1 className="text-xl sm:text-2xl font-semibold text-gray-900 break-words">
            {property ? (
              <Link to={`/properties/${contract.property_id}`} className="hover:text-blue-600">
                {property.address}
              </Link>
            ) : (
              `Договор #${contract.id.slice(0, 8)}`
            )}
          </h1>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-600">
            {tenant ? (
              <span className="inline-flex flex-wrap items-center gap-2">
                <span className="font-medium text-gray-800">{tenant.full_name}</span>
                {tenant.phone && (
                  <a
                    href={`tel:${tenant.phone}`}
                    className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800"
                  >
                    <Phone className="h-3.5 w-3.5" />
                    {tenant.phone}
                  </a>
                )}
              </span>
            ) : (
              <span>{contract.tenant_id}</span>
            )}
            <span className="inline-flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${statusDots[contract.status] || 'bg-gray-400'}`} />
              {statusLabels[contract.status] || contract.status}
            </span>
            {(ledger?.overdue_days ?? 0) > 0 ? (
              <span className="text-red-600 font-medium">
                просрочка {ledger!.overdue_days} дн.
              </span>
            ) : (
              endLabel && contract.status !== 'draft' && (
                <span className="text-gray-500">{endLabel}</span>
              )
            )}
            {(ledger?.overdue_days ?? 0) > 0 && endLabel && (
              <span className="text-gray-400">· до конца {endLabel.replace(/^осталось /, '')}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 w-full lg:w-auto">
          {canPay && (
            <Button
              leftIcon={<Wallet className="h-4 w-4" />}
              onClick={() => openPayment()}
              className="flex-1 lg:flex-none"
            >
              <span className="sm:hidden">Платёж</span>
              <span className="hidden sm:inline">Внести платёж</span>
            </Button>
          )}
          <Button
            variant="secondary"
            leftIcon={<RefreshCw className="h-4 w-4" />}
            onClick={() => void refreshAll()}
            className="shrink-0"
            aria-label="Обновить"
          >
            <span className="hidden sm:inline">Обновить</span>
          </Button>
          <ActionMenu items={menuItems} />
        </div>
      </div>

      {/* Баланс */}
      <Card>
        {ledger ? (
          <div className="space-y-4">
            <div>
              {outstanding < 0 ? (
                <>
                  <p className="text-sm text-gray-500 mb-1">Аванс</p>
                  <p className="text-3xl font-semibold tabular-nums text-blue-600">
                    {money(Math.abs(outstanding), contract.currency)}
                  </p>
                  <p className="text-sm text-gray-500 mt-1">Оплачено вперёд — спишется с следующих начислений</p>
                </>
              ) : outstanding > 0 ? (
                <>
                  <p className="text-sm text-gray-500 mb-1">К получению</p>
                  <p className="text-3xl font-semibold tabular-nums text-red-600">
                    {money(outstanding, contract.currency)}
                  </p>
                  {nextOpen && (
                    <p className="text-sm text-gray-500 mt-1">
                      {nextOpen.status === 'overdue' ? 'Самое раннее' : 'Ближайшее'}:{' '}
                      {formatDate(nextOpen.due_date)} — остаток{' '}
                      {money(chargeRemaining(nextOpen), contract.currency)}
                    </p>
                  )}
                </>
              ) : (
                <>
                  <p className="text-sm text-gray-500 mb-1">Баланс</p>
                  <p className="text-3xl font-semibold tabular-nums text-emerald-600">Сведено</p>
                  <p className="text-sm text-gray-500 mt-1">Начисления и оплаты совпадают</p>
                </>
              )}
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm border-t border-gray-100 pt-3">
              <div>
                <span className="text-gray-500">Начислено </span>
                <span className="font-medium">{money(ledger.total_expected || 0, contract.currency)}</span>
              </div>
              <div>
                <span className="text-gray-500">Оплачено </span>
                <span className="font-medium text-emerald-600">{money(ledger.total_paid || 0, contract.currency)}</span>
              </div>
              {ledger.last_payment_date && (
                <div>
                  <span className="text-gray-500">Последний платёж </span>
                  <span>{formatDate(ledger.last_payment_date)}</span>
                </div>
              )}
              {ledger.overdue_days > 0 && (
                <div>
                  <span className="text-gray-500">Просрочка </span>
                  <span className={ledger.overdue_days > 60 ? 'text-red-600 font-medium' : 'text-orange-600'}>
                    {ledger.overdue_days} дн.
                  </span>
                </div>
              )}
            </div>
            {deposit !== null && (
              <p className="text-xs text-gray-500 border-t border-gray-100 pt-3">
                Депозит {money(deposit, contract.currency)} — вне учёта аренды (только в договоре)
              </p>
            )}
            {contract.termination_reason && (
              <p className="text-sm text-amber-800 bg-amber-50 rounded-lg px-3 py-2">
                Причина расторжения: {contract.termination_reason}
              </p>
            )}
          </div>
        ) : (
          <p className="text-sm text-gray-500">Нет финансовых данных</p>
        )}

        <div className="mt-4 pt-3 border-t border-gray-100 flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-600">
          <span>
            Аренда {money(contract.rent_amount, contract.currency)} ·{' '}
            {contract.billing_period === 'monthly'
              ? 'ежемесячно'
              : contract.billing_period === 'quarterly'
                ? 'ежеквартально'
                : 'ежегодно'}
          </span>
          <span>
            {formatDate(contract.start_date)} — {formatDate(contract.end_date)}
          </span>
          <span>Платёж {contract.payment_day}-го числа</span>
        </div>
      </Card>

      {/* Табы */}
      <div className="rounded-xl bg-white shadow-sm border border-gray-200 overflow-hidden">
        <div className="flex border-b border-gray-100 overflow-x-auto [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`flex-1 sm:flex-none px-3 sm:px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors border-b-2 -mb-px ${
                tab === t.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="p-3 sm:p-5">
          {tab === 'periods' && (
            <>
              {!charges ? (
                <LedgerSkeleton />
              ) : chargeList.length === 0 ? (
                contract.status === 'draft' ? (
                  <EmptyState
                    icon={FileText}
                    title="Черновик без начислений"
                    description="Активируйте договор — начисления создадутся автоматически, если включена автогенерация. Или сгенерируйте вручную."
                    action={{
                      label: 'Активировать',
                      onClick: () => setActivateOpen(true),
                    }}
                  />
                ) : canWriteCharges ? (
                  <EmptyState
                    icon={FileText}
                    title="Начислений пока нет"
                    description="Запустите генерацию начислений по расписанию договора."
                    action={{
                      label: generateMutation.isPending ? 'Запуск…' : 'Сгенерировать',
                      onClick: () => generateMutation.mutate(),
                    }}
                  />
                ) : (
                  <EmptyState
                    icon={FileText}
                    title="Начислений пока нет"
                    description="Начисления ещё не созданы по этому договору."
                  />
                )
              ) : (
                <div className="space-y-4">
                  {openCharges.length === 0 ? (
                    <p className="text-sm text-emerald-700 bg-emerald-50 rounded-lg px-3 py-2">
                      Все открытые периоды оплачены
                    </p>
                  ) : (
                    <ChargePeriodsList
                      charges={openCharges}
                      currency={contract.currency}
                      canPay={canPay}
                      onPay={openPayment}
                    />
                  )}

                  {paidCharges.length > 0 && (
                    <div className="space-y-3">
                      <button
                        type="button"
                        onClick={() => setShowPaid((v) => !v)}
                        className="text-sm text-gray-500 hover:text-gray-800 min-h-10"
                      >
                        {showPaid ? 'Скрыть оплаченные' : `Показать оплаченные (${paidCharges.length})`}
                      </button>
                      {showPaid && (
                        <ChargePeriodsList
                          charges={paidCharges}
                          currency={contract.currency}
                          canPay={false}
                          muted
                        />
                      )}
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {tab === 'ledger' && (
            <>
              {!ledger?.lines?.length ? (
                <p className="text-sm text-gray-500 py-6 text-center">Кассовых операций пока нет</p>
              ) : (
                <LedgerTable lines={ledger.lines} currency={contract.currency} />
              )}
            </>
          )}

          {tab === 'events' && <ContractTimeline contractId={contract.id} />}
        </div>
      </div>

      <AttachmentsSection parentType="contract" parentId={contract.id} />

      <PaymentModal
        isOpen={paymentOpen}
        onClose={() => {
          setPaymentOpen(false);
          setPaymentChargeId(undefined);
        }}
        defaultContractId={contract.id}
        defaultChargeId={paymentChargeId}
      />
      <TerminateContractWizard
        isOpen={terminateOpen}
        onClose={() => setTerminateOpen(false)}
        contract={contract}
      />
      <RenewContractWizard isOpen={renewOpen} onClose={() => setRenewOpen(false)} contract={contract} />
      <ConfirmDialog
        isOpen={activateOpen}
        onClose={() => setActivateOpen(false)}
        onConfirm={() => activateMutation.mutate()}
        title="Активировать договор?"
        message="Договор станет активным. При включённой автогенерации начисления создадутся в фоне."
        isLoading={activateMutation.isPending}
      />
    </div>
  );
}
