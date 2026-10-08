import type { Contract, Ledger } from '@/entities/contract';
import { Card } from '@/shared/ui/Card';
import { formatDate } from '@/shared/lib/utils';
import { chargeRemaining, formatContractMoney } from '@/features/contracts/lib/display';
import type { ChargeRow } from '@/features/contracts/components/ChargePeriodsList';

interface ContractBalanceCardProps {
  contract: Contract;
  ledger: Ledger | undefined;
  nextOpen: ChargeRow | null;
}

export function ContractBalanceCard({ contract, ledger, nextOpen }: ContractBalanceCardProps) {
  const outstanding = Number(ledger?.outstanding_balance || 0);
  const deposit = contract.deposit_amount && Number(contract.deposit_amount) > 0
    ? Number(contract.deposit_amount)
    : null;

  return (
    <Card>
      {ledger ? (
        <div className="space-y-4">
          <div>
            {outstanding < 0 ? (
              <>
                <p className="text-sm text-gray-500 mb-1">Аванс</p>
                <p className="text-3xl font-semibold tabular-nums text-blue-600">
                  {formatContractMoney(Math.abs(outstanding), contract.currency)}
                </p>
                <p className="text-sm text-gray-500 mt-1">Оплачено вперёд — спишется с следующих начислений</p>
              </>
            ) : outstanding > 0 ? (
              <>
                <p className="text-sm text-gray-500 mb-1">К получению</p>
                <p className="text-3xl font-semibold tabular-nums text-red-600">
                  {formatContractMoney(outstanding, contract.currency)}
                </p>
                {nextOpen && (
                  <p className="text-sm text-gray-500 mt-1">
                    {nextOpen.status === 'overdue' ? 'Самое раннее' : 'Ближайшее'}:{' '}
                    {formatDate(nextOpen.due_date)} — остаток{' '}
                    {formatContractMoney(chargeRemaining(nextOpen), contract.currency)}
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
              <span className="font-medium">{formatContractMoney(ledger.total_expected || 0, contract.currency)}</span>
            </div>
            <div>
              <span className="text-gray-500">Оплачено </span>
              <span className="font-medium text-emerald-600">{formatContractMoney(ledger.total_paid || 0, contract.currency)}</span>
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
              Депозит {formatContractMoney(deposit, contract.currency)} — вне учёта аренды (только в договоре)
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
          Аренда {formatContractMoney(contract.rent_amount, contract.currency)} ·{' '}
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
  );
}
