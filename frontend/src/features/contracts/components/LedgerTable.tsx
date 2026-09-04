import { motion } from 'framer-motion';
import type { LedgerLine } from '@/entities/contract';
import { formatDate } from '@/shared/lib/utils';

interface LedgerTableProps {
  lines: LedgerLine[];
  currency: string;
}

const METHOD_LABELS: Record<string, string> = {
  transfer: 'перевод',
  cash: 'наличные',
  card: 'карта',
  bank: 'банк',
};

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.04 } } };
const row = { hidden: { opacity: 0, y: 4 }, show: { opacity: 1, y: 0 } };

function formatMoney(amount: number, currency: string): string {
  const suffix = currency === 'RUB' ? '₽' : currency;
  return `${Math.abs(amount).toLocaleString('ru-RU')} ${suffix}`;
}

/** Заголовок операции без дубля типа из соседней колонки. */
function operationLabel(line: LedgerLine): string {
  if (line.type === 'charge') {
    const match = line.description.match(/период\s+(.+)/i);
    return match ? `Начислено · ${match[1]}` : 'Начислено';
  }
  const match = line.description.match(/\(([^)]+)\)/);
  const method = match?.[1] ? METHOD_LABELS[match[1]] || match[1] : null;
  return method ? `Получено · ${method}` : 'Получено';
}

/** Состояние счёта после операции — не результат самой операции. */
function balanceLabel(balance: number, currency: string): { text: string; className: string } {
  if (balance > 0) {
    return { text: formatMoney(balance, currency), className: 'text-amber-600' };
  }
  if (balance < 0) {
    return { text: `аванс ${formatMoney(balance, currency)}`, className: 'text-blue-600' };
  }
  return { text: formatMoney(0, currency), className: 'text-emerald-600' };
}

export function LedgerTable({ lines, currency }: LedgerTableProps) {
  // Новые сверху — привычный порядок для «истории»
  const ordered = [...lines].reverse();

  return (
    <div>
      <p className="text-xs text-gray-500 mb-3">
        Справа — состояние <span className="text-gray-600">после</span> операции: сколько ещё ждать
        или сколько аванса уже оплачено вперёд. Начисление само аванс не создаёт — оно только
        списывает его.
      </p>
      <motion.div variants={container} initial="hidden" animate="show" className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs uppercase tracking-wide text-gray-500">
              <th className="py-2 font-medium">Дата</th>
              <th className="py-2 font-medium">Операция</th>
              <th className="py-2 font-medium text-right">Сумма</th>
              <th className="py-2 font-medium text-right">После операции</th>
            </tr>
          </thead>
          <tbody>
            {ordered.map((line, i) => {
              const amount = Number(line.amount);
              const balance = Number(line.balance);
              const isPayment = line.type === 'payment';
              const after = balanceLabel(balance, currency);

              return (
                <motion.tr key={`${line.date}-${line.type}-${i}`} variants={row} className="border-b last:border-0">
                  <td className="py-2.5 text-gray-600 whitespace-nowrap">{formatDate(line.date)}</td>
                  <td className="py-2.5 text-gray-800">{operationLabel(line)}</td>
                  <td
                    className={`py-2.5 text-right font-medium tabular-nums whitespace-nowrap ${
                      isPayment ? 'text-emerald-600' : 'text-gray-900'
                    }`}
                  >
                    {isPayment ? '+' : ''}
                    {formatMoney(amount, currency)}
                  </td>
                  <td className={`py-2.5 text-right font-medium tabular-nums whitespace-nowrap ${after.className}`}>
                    {after.text}
                  </td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </motion.div>
    </div>
  );
}
