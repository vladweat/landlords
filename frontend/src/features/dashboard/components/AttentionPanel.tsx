import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowRight, CalendarClock, Wallet, X } from 'lucide-react';
import { DashboardSection } from './DashboardSection';

interface AttentionPanelProps {
  overdueChargesCount: number;
  overdueChargesAmount: string;
  overdueContractsCount: number;
  remainingToCollect: number;
  collected: number;
  expected: number;
}

function overdueChargesLabel(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return `${count} просроченное начисление`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return `${count} просроченных начисления`;
  }
  return `${count} просроченных начислений`;
}

function overdueContractsLabel(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return `${count} договор с просрочкой оплаты`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return `${count} договора с просрочкой оплаты`;
  }
  return `${count} договоров с просрочкой оплаты`;
}

/** Единая зона «Требует внимания»: начисления, договоры и прогресс сбора за месяц. */
export function AttentionPanel({
  overdueChargesCount,
  overdueChargesAmount,
  overdueContractsCount,
  remainingToCollect,
  collected,
  expected,
}: AttentionPanelProps) {
  const dismissKey = useMemo(
    () =>
      `attention_dismissed_${overdueChargesCount}_${overdueChargesAmount}_${overdueContractsCount}`,
    [overdueChargesCount, overdueChargesAmount, overdueContractsCount],
  );
  const [dismissed, setDismissed] = useState(() => sessionStorage.getItem(dismissKey) === 'true');

  useEffect(() => {
    setDismissed(sessionStorage.getItem(dismissKey) === 'true');
  }, [dismissKey]);

  const progress =
    expected > 0 ? Math.min(100, Math.round((collected / expected) * 100)) : collected > 0 ? 100 : 0;
  const hasAlerts = overdueChargesCount > 0 || overdueContractsCount > 0;
  const showAlerts = hasAlerts && !dismissed;

  return (
    <DashboardSection title="Сегодня" icon={<Wallet className="h-4 w-4 text-blue-600" />}>
      <div className="space-y-4">
        <div>
          <div className="flex items-end justify-between gap-3 mb-2">
            <div>
              <p className="text-xs text-gray-500">Сбор аренды за месяц</p>
              <p className="text-lg font-semibold text-gray-900 tabular-nums">
                {collected.toLocaleString('ru-RU')} ₽
                <span className="text-sm font-normal text-gray-400">
                  {' '}
                  / {expected.toLocaleString('ru-RU')} ₽
                </span>
              </p>
            </div>
            <p className="text-sm text-gray-600 tabular-nums">
              осталось {remainingToCollect.toLocaleString('ru-RU')} ₽
            </p>
          </div>
          <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
            <div
              className="h-full rounded-full bg-emerald-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {showAlerts ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Требует внимания
              </p>
              <button
                type="button"
                onClick={() => {
                  sessionStorage.setItem(dismissKey, 'true');
                  setDismissed(true);
                }}
                className="p-1 text-gray-400 hover:text-gray-600"
                aria-label="Скрыть предупреждения"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>

            {overdueChargesCount > 0 && (
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5">
                <div className="flex items-start gap-2 min-w-0">
                  <AlertTriangle className="h-4 w-4 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-900">
                    {overdueChargesLabel(overdueChargesCount)} на{' '}
                    <span className="font-medium">
                      {Number(overdueChargesAmount).toLocaleString('ru-RU')} ₽
                    </span>
                  </p>
                </div>
                <Link
                  to="/calendar"
                  className="inline-flex items-center gap-1 text-sm font-medium text-red-700 hover:text-red-900 flex-shrink-0"
                >
                  К начислениям <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            )}

            {overdueContractsCount > 0 && (
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5">
                <div className="flex items-start gap-2 min-w-0">
                  <CalendarClock className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-amber-900">
                    {overdueContractsLabel(overdueContractsCount)} — проверьте статус или продление
                  </p>
                </div>
                <Link
                  to="/contracts?status=overdue"
                  className="inline-flex items-center gap-1 text-sm font-medium text-amber-800 hover:text-amber-950 flex-shrink-0"
                >
                  Открыть <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            )}
          </div>
        ) : hasAlerts && dismissed ? (
          <p className="text-xs text-gray-400">Предупреждения скрыты до обновления данных</p>
        ) : (
          <p className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2">
            Просрочек нет — можно планировать следующие платежи
          </p>
        )}
      </div>
    </DashboardSection>
  );
}
