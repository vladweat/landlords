import { useNavigate, Link } from 'react-router-dom';
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
import { showError, showSuccess } from '@/shared/lib/toast';
import { apiClient, authorizedFetch } from '@/shared/api/client';
import { contractsApi } from '@/features/contracts/api';
import { propertiesApi } from '@/features/properties/api';
import { tenantsApi } from '@/features/tenants/api';
import { paymentsApi } from '@/features/payments/api';
import { portalApi } from '@/features/portal/api';
import { useCan } from '@/features/auth/permissions';
import { Button } from '@/shared/ui/Button';
import { Card } from '@/shared/ui/Card';
import { Skeleton } from '@/shared/ui/Skeleton';
import { ActionMenu } from '@/shared/ui/ActionMenu';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import type { ChargeRow } from '@/features/contracts/components/ChargePeriodsList';
import { TerminateContractWizard } from '@/features/contracts/components/TerminateContractWizard';
import { AttachmentsSection } from '@/features/documents/components/AttachmentsSection';
import { RenewContractWizard } from '@/features/contracts/components/RenewContractWizard';
import { PaymentModal } from '@/features/payments/components/PaymentModal';
import { ContractBalanceCard } from '@/features/contracts/components/ContractBalanceCard';
import { ContractFinanceTabs } from '@/features/contracts/components/ContractFinanceTabs';
import { TenantPaymentClaimBanner } from '@/features/contracts/components/TenantPaymentClaimBanner';
import { contractStatusDots, contractStatusLabels, daysLeftLabel } from '@/features/contracts/lib/display';
import { copyToClipboard } from '@/shared/lib/clipboard';

type TabId = 'periods' | 'ledger' | 'events';

const UNPAID = new Set(['pending', 'overdue', 'partially_paid']);

interface ContractWorkspaceProps {
  contractId: string;
}

export function ContractWorkspace({ contractId }: ContractWorkspaceProps) {
  const id = contractId;
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
      showSuccess('Договор активирован');
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
      showSuccess('Генерация начислений запущена');
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
      await copyToClipboard(data.share_url, false);
      const expiresAt = new Date(data.portal_token_expires_at).toLocaleString();
      showSuccess(`Ссылка скопирована. Действует до ${expiresAt}`);
    },
    onError: (error) => showError(error, 'Не удалось получить ссылку'),
  });

  const dismissClaimMutation = useMutation({
    mutationFn: (claimId: string) => portalApi.dismissClaim(claimId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract-claims', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-events', id] });
      showSuccess('Заявка отклонена');
    },
    onError: (error) => showError(error, 'Не удалось отклонить заявку'),
  });

  const confirmClaimMutation = useMutation({
    mutationFn: (claimId: string) => portalApi.confirmClaim(claimId),
    retry: 0,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract-claims', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-events', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-ledger', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-charges', id] });
      queryClient.invalidateQueries({ queryKey: ['payments'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      showSuccess('Платёж проведён');
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
  const endLabel = daysLeftLabel(contract.end_date);

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
      showSuccess('Данные обновлены');
    } catch (error) {
      showError(error, 'Не удалось обновить');
    }
  };

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
          const res = await apiClient.post<{ status: string; data: { url: string } }>(
            `/contracts/${contract.id}/document`,
          );
          const fileRes = await authorizedFetch(res.data.data.url);
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
        <TenantPaymentClaimBanner
          claim={pendingClaim}
          currency={contract.currency}
          canConfirm={canWritePayments}
          isDismissing={dismissClaimMutation.isPending}
          isConfirming={confirmClaimMutation.isPending}
          onDismiss={() => dismissClaimMutation.mutate(pendingClaim.id)}
          onConfirm={() => confirmClaimMutation.mutate(pendingClaim.id)}
        />
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
              <span className={`w-2 h-2 rounded-full ${contractStatusDots[contract.status] || 'bg-gray-400'}`} />
              {contractStatusLabels[contract.status] || contract.status}
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

      <ContractBalanceCard contract={contract} ledger={ledger} nextOpen={nextOpen} />

      <ContractFinanceTabs
        tab={tab}
        onTab={setTab}
        contractId={contract.id}
        contractStatus={contract.status}
        currency={contract.currency}
        charges={charges as ChargeRow[] | undefined}
        openCharges={openCharges}
        paidCharges={paidCharges}
        showPaid={showPaid}
        onTogglePaid={() => setShowPaid((v) => !v)}
        canPay={canPay}
        canWriteCharges={canWriteCharges}
        isGenerating={generateMutation.isPending}
        onPay={openPayment}
        onActivate={() => setActivateOpen(true)}
        onGenerate={() => generateMutation.mutate()}
        ledger={ledger}
      />

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
