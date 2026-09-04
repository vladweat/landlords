import { useParams, useNavigate, Link } from 'react-router-dom';
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, ChevronDown, ChevronUp, FileX, RefreshCw } from 'lucide-react';
import { contractsApi } from '@/features/contracts/api';
import { propertiesApi } from '@/features/properties/api';
import { tenantsApi } from '@/features/tenants/api';
import { paymentsApi } from '@/features/payments/api';
import { Card } from '@/shared/ui/Card';
import { Button } from '@/shared/ui/Button';
import { Skeleton, LedgerSkeleton } from '@/shared/ui/Skeleton';
import { LedgerTable } from '@/features/contracts/components/LedgerTable';
import { ReminderButton } from '@/features/reminders/components/ReminderButton';
import { DownloadContractButton } from '@/features/contracts/components/DownloadContractButton';
import { TerminateContractWizard } from '@/features/contracts/components/TerminateContractWizard';
import { RenewContractWizard } from '@/features/contracts/components/RenewContractWizard';
import { ContractTimeline } from '@/features/contracts/components/ContractTimeline';
import { copyToClipboard } from '@/shared/lib/clipboard';
import { formatDate } from '@/shared/lib/utils';

function operationsLabel(count: number): string {
  const n = Math.abs(count) % 100;
  const n1 = n % 10;
  if (n > 10 && n < 20) return `${count} операций`;
  if (n1 === 1) return `${count} операция`;
  if (n1 >= 2 && n1 <= 4) return `${count} операции`;
  return `${count} операций`;
}

const statusLabels: Record<string, string> = {
  draft: 'Черновик', active: 'Активен', ended: 'Завершён', overdue: 'Просрочен', terminated: 'Расторгнут',
};

const statusDots: Record<string, string> = {
  draft: 'bg-gray-400', active: 'bg-emerald-500', ended: 'bg-blue-500', overdue: 'bg-red-500', terminated: 'bg-amber-500',
};

export default function ContractDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [terminateOpen, setTerminateOpen] = useState(false);
  const [renewOpen, setRenewOpen] = useState(false);
  const [ledgerExpanded, setLedgerExpanded] = useState(false);

  const { data: contract, isLoading: contractLoading } = useQuery({ queryKey: ['contract', id], queryFn: () => contractsApi.getById(id!), enabled: !!id });
  const { data: propertiesData, isLoading: propsLoading } = useQuery({ queryKey: ['properties'], queryFn: () => propertiesApi.getAll({ per_page: 100 }) });
  const { data: tenantsData, isLoading: tenantsLoading } = useQuery({ queryKey: ['tenants'], queryFn: () => tenantsApi.getAll({ per_page: 100 }) });
  const { data: ledger } = useQuery({ queryKey: ['contract-ledger', id], queryFn: () => contractsApi.getLedger(id!), enabled: !!id });
  const { data: charges } = useQuery({ queryKey: ['contract-charges', id], queryFn: () => paymentsApi.getCharges(id!), enabled: !!id });

  const isLoading = contractLoading || propsLoading || tenantsLoading;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-6 w-32" />
        <div className="flex items-center justify-between"><Skeleton className="h-8 w-48" /><Skeleton className="h-6 w-24 rounded-full" /></div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card><Skeleton className="h-5 w-24 mb-4" />{[1,2,3,4,5,6,7].map((i)=><Skeleton key={i} className="h-4 w-full mb-2"/>)}</Card>
          <Card><Skeleton className="h-5 w-24 mb-4" />{[1,2,3].map((i)=><Skeleton key={i} className="h-4 w-full mb-2"/>)}</Card>
        </div>
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

  return (
    <div className="space-y-6">
      <button onClick={() => navigate('/contracts')} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900"><ArrowLeft className="h-4 w-4" /> Назад</button>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">
          Договор{' '}
          <button onClick={() => copyToClipboard(contract.id)} className="hover:text-blue-600 cursor-pointer" title="Копировать ID">#{contract.id.slice(0,8)}</button>
        </h1>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-2 text-sm text-gray-700">
            <span className={`w-2 h-2 rounded-full ${statusDots[contract.status] || 'bg-gray-400'}`} />
            {statusLabels[contract.status] || contract.status}
          </span>
          <button
            onClick={async () => {
              await contractsApi.refreshStatus(contract.id);
              queryClient.invalidateQueries({ queryKey: ['contract', id] });
            }}
            className="text-xs text-gray-400 hover:text-blue-600 transition-colors"
          >
            Обновить
          </button>
          {canRenew && (
            <Button variant="secondary" leftIcon={<RefreshCw className="h-4 w-4" />} onClick={() => setRenewOpen(true)}>
              Продлить
            </Button>
          )}
          {canTerminate && (
            <Button variant="danger" leftIcon={<FileX className="h-4 w-4" />} onClick={() => setTerminateOpen(true)}>
              Расторгнуть
            </Button>
          )}
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="text-lg font-medium text-gray-800 mb-3">Детали</h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between gap-4">
              <span className="text-gray-500 shrink-0">Объект</span>
              <Link to={`/properties/${contract.property_id}`} className="text-right text-blue-600 hover:text-blue-800">
                {property?.address || contract.property_id}
              </Link>
            </div>
            <div className="flex justify-between"><span className="text-gray-500">Арендатор</span><span>{tenant?.full_name||contract.tenant_id}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Сумма</span><span>{Number(contract.rent_amount).toLocaleString('ru-RU')} {contract.currency}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Период</span><span>{contract.start_date} — {contract.end_date}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">День платежа</span><span>{contract.payment_day} число</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Период оплаты</span><span>{contract.billing_period==='monthly'?'Ежемесячно':contract.billing_period==='quarterly'?'Ежеквартально':'Ежегодно'}</span></div>
            {contract.deposit_amount && Number(contract.deposit_amount)>0 && <div className="flex justify-between"><span className="text-gray-500">Депозит</span><span>{Number(contract.deposit_amount).toLocaleString('ru-RU')} {contract.currency}</span></div>}
            {contract.termination_reason && (
              <div className="flex justify-between gap-4">
                <span className="text-gray-500 shrink-0">Причина расторжения</span>
                <span className="text-right">{contract.termination_reason}</span>
              </div>
            )}
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100">
            <DownloadContractButton contractId={contract.id} />
          </div>
        </Card>
        <Card><h2 className="text-lg font-medium text-gray-800 mb-3">Финансы</h2>
          {ledger ? <div className="space-y-3 text-sm">
            <div className="flex justify-between"><span className="text-gray-500">Начислено</span><span>{Number(ledger.total_expected||0).toLocaleString('ru-RU')} {contract.currency}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Оплачено</span><span className="text-emerald-600">{Number(ledger.total_paid||0).toLocaleString('ru-RU')} {contract.currency}</span></div>
            <div className="border-t pt-2 flex justify-between"><span className="font-medium">Ожидает оплаты</span><span className={`font-semibold ${Number(ledger.outstanding_balance||0)>0?'text-red-600':'text-emerald-600'}`}>{Number(ledger.outstanding_balance||0).toLocaleString('ru-RU')} {contract.currency}</span></div>
            {ledger.last_payment_date && <div className="flex justify-between"><span className="text-gray-500">Последний платёж</span><span>{formatDate(ledger.last_payment_date)}</span></div>}
            {ledger.overdue_days > 0 && <div className="flex justify-between"><span className="text-gray-500">Просрочка</span><span className={ledger.overdue_days > 60 ? 'text-red-600 font-medium' : 'text-orange-600'}>{ledger.overdue_days} дн.</span></div>}
          </div> : <p className="text-sm text-gray-500">Нет данных</p>}
        </Card>
      </div>
      <Card><h2 className="text-lg font-medium text-gray-800 mb-3">Начисления</h2>
        {!charges ? <LedgerSkeleton /> : charges.length === 0 ? <p className="text-sm text-gray-500">Начислений пока нет</p> : (
          <table className="w-full text-sm"><thead><tr className="text-xs uppercase tracking-wide text-gray-500 border-b"><th className="py-2 text-left font-medium">Дата</th><th className="py-2 text-left font-medium">Период</th><th className="py-2 text-left font-medium">Сумма</th><th className="py-2 text-left font-medium">Статус</th><th className="py-2 text-left font-medium">Действие</th></tr></thead>
          <tbody>{charges.map((c:{id:string;due_date:string;period_start:string;period_end:string;amount:string;status:string})=>{
            return (
              <tr key={c.id} className="border-b last:border-0">
                <td className="py-2">{c.due_date}</td><td className="py-2 text-gray-500">{c.period_start} — {c.period_end}</td><td className="py-2">{Number(c.amount).toLocaleString('ru-RU')} {contract.currency}</td>
                <td className="py-2"><span className="inline-flex items-center gap-2 text-sm text-gray-700"><span className={`w-2 h-2 rounded-full ${c.status==='paid'?'bg-emerald-500':c.status==='overdue'?'bg-red-500':'bg-gray-400'}`} />{c.status==='paid'?'Оплачен':c.status==='overdue'?'Просрочен':'Ожидает'}</span></td>
                <td className="py-2">{c.status === 'overdue' && <ReminderButton chargeId={c.id} chargeStatus={c.status} />}</td>
              </tr>
            );
          })}</tbody></table>
        )}
      </Card>

      <Card>
        <h2 className="text-lg font-medium text-gray-800 mb-3">История</h2>
        <ContractTimeline contractId={contract.id} />
      </Card>

      {ledger?.lines && ledger.lines.length > 0 && (
        <Card>
          <button
            type="button"
            onClick={() => setLedgerExpanded((v) => !v)}
            className="flex w-full items-center justify-between gap-2 text-left"
          >
            <h2 className="text-lg font-medium text-gray-800">История операций</h2>
            <span className="inline-flex items-center gap-1 text-sm text-gray-500">
              {operationsLabel(ledger.lines.length)}
              {ledgerExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </span>
          </button>
          {ledgerExpanded && (
            <div className="mt-3">
              <LedgerTable lines={ledger.lines} currency={contract.currency} />
            </div>
          )}
        </Card>
      )}

      <TerminateContractWizard isOpen={terminateOpen} onClose={() => setTerminateOpen(false)} contract={contract} />
      <RenewContractWizard isOpen={renewOpen} onClose={() => setRenewOpen(false)} contract={contract} />
    </div>
  );
}
