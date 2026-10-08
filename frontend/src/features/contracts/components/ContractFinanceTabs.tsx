import { FileText } from 'lucide-react';
import { EmptyState } from '@/shared/ui/EmptyState';
import { LedgerSkeleton } from '@/shared/ui/Skeleton';
import type { Ledger } from '@/entities/contract';
import { LedgerTable } from '@/features/contracts/components/LedgerTable';
import { ChargePeriodsList, type ChargeRow } from '@/features/contracts/components/ChargePeriodsList';
import { ContractTimeline } from '@/features/contracts/components/ContractTimeline';

type TabId = 'periods' | 'ledger' | 'events';

interface LedgerLines {
  lines?: Ledger['lines'];
}

interface ContractFinanceTabsProps {
  tab: TabId;
  onTab: (tab: TabId) => void;
  contractId: string;
  contractStatus: string;
  currency: string;
  charges: ChargeRow[] | undefined;
  openCharges: ChargeRow[];
  paidCharges: ChargeRow[];
  showPaid: boolean;
  onTogglePaid: () => void;
  canPay: boolean;
  canWriteCharges: boolean;
  isGenerating: boolean;
  onPay: (chargeId?: string) => void;
  onActivate: () => void;
  onGenerate: () => void;
  ledger: LedgerLines | undefined;
}

const tabs: { id: TabId; label: string }[] = [
  { id: 'periods', label: 'Периоды' },
  { id: 'ledger', label: 'Касса' },
  { id: 'events', label: 'События' },
];

export function ContractFinanceTabs({
  tab,
  onTab,
  contractId,
  contractStatus,
  currency,
  charges,
  openCharges,
  paidCharges,
  showPaid,
  onTogglePaid,
  canPay,
  canWriteCharges,
  isGenerating,
  onPay,
  onActivate,
  onGenerate,
  ledger,
}: ContractFinanceTabsProps) {
  const chargeList = charges ?? [];

  return (
    <div className="rounded-xl bg-white shadow-sm border border-gray-200 overflow-hidden">
      <div className="flex border-b border-gray-100 overflow-x-auto [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => onTab(t.id)}
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
              contractStatus === 'draft' ? (
                <EmptyState
                  icon={FileText}
                  title="Черновик без начислений"
                  description="Активируйте договор — начисления создадутся автоматически, если включена автогенерация. Или сгенерируйте вручную."
                  action={{ label: 'Активировать', onClick: onActivate }}
                />
              ) : canWriteCharges ? (
                <EmptyState
                  icon={FileText}
                  title="Начислений пока нет"
                  description="Запустите генерацию начислений по расписанию договора."
                  action={{
                    label: isGenerating ? 'Запуск…' : 'Сгенерировать',
                    onClick: onGenerate,
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
                    currency={currency}
                    canPay={canPay}
                    onPay={onPay}
                  />
                )}
                {paidCharges.length > 0 && (
                  <div className="space-y-3">
                    <button
                      type="button"
                      onClick={onTogglePaid}
                      className="text-sm text-gray-500 hover:text-gray-800 min-h-10"
                    >
                      {showPaid ? 'Скрыть оплаченные' : `Показать оплаченные (${paidCharges.length})`}
                    </button>
                    {showPaid && (
                      <ChargePeriodsList charges={paidCharges} currency={currency} canPay={false} muted />
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
              <LedgerTable lines={ledger.lines} currency={currency} />
            )}
          </>
        )}

        {tab === 'events' && <ContractTimeline contractId={contractId} />}
      </div>
    </div>
  );
}
