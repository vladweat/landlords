import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, X, ArrowRight } from 'lucide-react';

interface OverdueAlertProps {
  count: number;
  amount: string;
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

export function OverdueAlert({ count, amount }: OverdueAlertProps) {
  const dismissedKey = 'overdue_alert_dismissed';
  const [dismissed, setDismissed] = useState(sessionStorage.getItem(dismissedKey) === 'true');

  if (dismissed || count === 0) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-amber-800">
              У вас {overdueChargesLabel(count)} на сумму {Number(amount).toLocaleString('ru-RU')} ₽
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 ml-4 flex-shrink-0">
          <Link to="/calendar" className="flex items-center gap-1 text-sm font-medium text-amber-700 hover:text-amber-900 transition-colors">
            Просмотреть <ArrowRight className="h-4 w-4" />
          </Link>
          <button
            onClick={() => { sessionStorage.setItem(dismissedKey, 'true'); setDismissed(true); }}
            className="p-1 text-amber-400 hover:text-amber-600 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
