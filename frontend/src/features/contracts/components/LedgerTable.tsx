import { motion } from 'framer-motion';
import { ArrowUp, ArrowDown } from 'lucide-react';
import type { LedgerLine } from '@/entities/contract';
import { formatDate } from '@/shared/lib/utils';

interface LedgerTableProps {
  lines: LedgerLine[];
  currency: string;
}

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
const row = { hidden: { opacity: 0, x: -10 }, show: { opacity: 1, x: 0 } };

function formatAmount(amount: string, currency: string): string {
  const num = Math.abs(Number(amount));
  return `${num.toLocaleString('ru-RU')} ${currency === 'RUB' ? '₽' : currency}`;
}

export function LedgerTable({ lines, currency }: LedgerTableProps) {
  return (
    <motion.div variants={container} initial="hidden" animate="show" className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500">
            <th className="py-2 font-medium">Дата</th>
            <th className="py-2 font-medium">Тип</th>
            <th className="py-2 font-medium">Описание</th>
            <th className="py-2 font-medium text-right">Сумма</th>
            <th className="py-2 font-medium text-right">Баланс</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line, i) => (
            <motion.tr key={i} variants={row} className="border-b last:border-0">
              <td className="py-2 text-gray-600">{formatDate(line.date)}</td>
              <td className="py-2">
                {line.type === 'charge' ? (
                  <span className="inline-flex items-center gap-1 text-gray-600"><ArrowUp className="h-3 w-3" /> Начисление</span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-green-600"><ArrowDown className="h-3 w-3" /> Платёж</span>
                )}
              </td>
              <td className="py-2 text-gray-500">{line.description}</td>
              <td className={`py-2 text-right font-medium ${line.type === 'payment' ? 'text-green-600' : 'text-gray-900'}`}>
                {line.type === 'payment' ? '+' : ''}{formatAmount(line.amount, currency)}
              </td>
              <td className="py-2 text-right font-medium">{formatAmount(line.balance, currency)}</td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </motion.div>
  );
}
