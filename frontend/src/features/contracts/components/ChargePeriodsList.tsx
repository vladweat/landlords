import { StatusDot } from '@/shared/ui/DetailTable';
import { DetailTable, DetailTd, DetailTh, DetailTr } from '@/shared/ui/DetailTable';
import { ReminderButton } from '@/features/reminders/components/ReminderButton';
import { InvoiceButton } from '@/features/invoices/components/InvoiceButton';
import { formatDate } from '@/shared/lib/utils';

export type ChargeRow = {
  id: string;
  due_date: string;
  period_start: string;
  period_end: string;
  amount: string;
  amount_paid?: string;
  status: string;
};

const chargeStatusLabels: Record<string, string> = {
  paid: 'Оплачен',
  overdue: 'Просрочен',
  partially_paid: 'Частично',
  pending: 'Ожидает',
};

const chargeStatusDots: Record<string, string> = {
  paid: 'bg-emerald-500',
  overdue: 'bg-red-500',
  partially_paid: 'bg-amber-500',
  pending: 'bg-gray-400',
};

function money(value: number | string, currency: string): string {
  const n = typeof value === 'string' ? Number(value) : value;
  const suffix = currency === 'RUB' ? '₽' : currency;
  return `${n.toLocaleString('ru-RU')} ${suffix}`;
}

function chargePaid(c: ChargeRow): number {
  return Number(c.amount_paid || 0);
}

function chargeRemaining(c: ChargeRow): number {
  return Math.max(0, Number(c.amount) - chargePaid(c));
}

function statusLabel(c: ChargeRow): string {
  const paid = chargePaid(c);
  if (c.status === 'overdue' && paid > 0) return 'Просрочен · частично';
  return chargeStatusLabels[c.status] || c.status;
}

interface ChargePeriodsListProps {
  charges: ChargeRow[];
  currency: string;
  canPay: boolean;
  muted?: boolean;
  onPay?: (chargeId: string) => void;
}

/** Карточки до lg, компактная таблица на широких экранах. */
export function ChargePeriodsList({
  charges,
  currency,
  canPay,
  muted,
  onPay,
}: ChargePeriodsListProps) {
  return (
    <>
      <ul className="space-y-3 lg:hidden">
        {charges.map((c) => {
          const remaining = chargeRemaining(c);
          const paid = chargePaid(c);
          return (
            <li
              key={c.id}
              className={`rounded-xl border border-gray-100 p-4 ${muted ? 'bg-gray-50/50 opacity-90' : 'bg-white'}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900">
                    Срок {formatDate(c.due_date)}
                  </p>
                  <p className="mt-0.5 text-xs text-gray-500">
                    {formatDate(c.period_start)} — {formatDate(c.period_end)}
                  </p>
                </div>
                <StatusDot
                  colorClass={chargeStatusDots[c.status] || 'bg-gray-400'}
                  label={statusLabel(c)}
                  muted={muted}
                />
              </div>
              <div className="mt-3 flex items-end justify-between gap-3">
                <div>
                  <p className="text-xs text-gray-500">{muted ? 'Сумма' : 'Остаток'}</p>
                  <p
                    className={`text-lg font-semibold tabular-nums ${
                      muted ? 'text-gray-500' : 'text-gray-900'
                    }`}
                  >
                    {money(muted ? c.amount : remaining, currency)}
                  </p>
                  {!muted && (
                    <p className="text-xs text-gray-400 tabular-nums">
                      из {money(c.amount, currency)}
                      {paid > 0 ? ` · оплачено ${money(paid, currency)}` : ''}
                    </p>
                  )}
                </div>
                {!muted && (
                  <div className="flex shrink-0 flex-col items-stretch gap-2">
                    {canPay && onPay && (
                      <button
                        type="button"
                        onClick={() => onPay(c.id)}
                        className="min-h-10 rounded-lg bg-blue-600 px-4 text-sm font-medium text-white hover:bg-blue-700"
                      >
                        Оплатить
                      </button>
                    )}
                    <InvoiceButton chargeId={c.id} />
                    {c.status === 'overdue' && (
                      <ReminderButton chargeId={c.id} chargeStatus={c.status} />
                    )}
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      <div className="hidden lg:block">
        <DetailTable>
          <thead>
            <tr>
              <DetailTh>Начисление</DetailTh>
              <DetailTh align="right">Остаток</DetailTh>
              <DetailTh>Статус</DetailTh>
              <DetailTh align="right"> </DetailTh>
            </tr>
          </thead>
          <tbody>
            {charges.map((c) => {
              const remaining = chargeRemaining(c);
              return (
                <DetailTr key={c.id} className={muted ? 'opacity-75' : undefined}>
                  <DetailTd wrap>
                    <div className="font-medium text-gray-900">{formatDate(c.due_date)}</div>
                    <div className="text-xs text-gray-500">
                      {formatDate(c.period_start)} — {formatDate(c.period_end)}
                    </div>
                    <div className="text-xs text-gray-400 tabular-nums">
                      {money(c.amount, currency)}
                      {!muted && chargePaid(c) > 0
                        ? ` · оплачено ${money(chargePaid(c), currency)}`
                        : ''}
                    </div>
                  </DetailTd>
                  <DetailTd
                    align="right"
                    mono
                    className={muted ? undefined : 'font-semibold text-gray-900'}
                    muted={muted}
                  >
                    {money(muted ? 0 : remaining, currency)}
                  </DetailTd>
                  <DetailTd>
                    <StatusDot
                      colorClass={chargeStatusDots[c.status] || 'bg-gray-400'}
                      label={statusLabel(c)}
                      muted={muted}
                    />
                  </DetailTd>
                  <DetailTd align="right" muted={muted}>
                    {muted ? (
                      '—'
                    ) : (
                      <div className="inline-flex items-center justify-end gap-3">
                        {canPay && onPay && (
                          <button
                            type="button"
                            onClick={() => onPay(c.id)}
                            className="text-sm font-medium text-blue-600 hover:text-blue-800"
                          >
                            Оплатить
                          </button>
                        )}
                        <InvoiceButton chargeId={c.id} compact />
                        {c.status === 'overdue' && (
                          <ReminderButton chargeId={c.id} chargeStatus={c.status} />
                        )}
                      </div>
                    )}
                  </DetailTd>
                </DetailTr>
              );
            })}
          </tbody>
        </DetailTable>
      </div>
    </>
  );
}
