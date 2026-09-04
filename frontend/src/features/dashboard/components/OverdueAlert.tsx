import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, X, ArrowRight } from 'lucide-react';

interface OverdueAlertProps {
  count: number;
  amount: string;
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
              У вас {count} просроченных платежа на сумму {Number(amount).toLocaleString('ru-RU')} ₽
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
