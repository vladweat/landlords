import { useEscapeKey } from '@/shared/hooks/useEscapeKey';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle } from 'lucide-react';
import { Button } from './Button';

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  isLoading?: boolean;
  confirmLabel?: string;
  confirmVariant?: 'primary' | 'danger';
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  isLoading,
  confirmLabel = 'Удалить',
  confirmVariant = 'danger',
}: ConfirmDialogProps) {
  useEscapeKey(onClose);
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/50"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
              <div className="flex items-center gap-3 mb-4">
                <div className={`flex h-10 w-10 items-center justify-center rounded-full ${confirmVariant === 'danger' ? 'bg-red-100' : 'bg-blue-100'}`}>
                  <AlertTriangle className={`h-5 w-5 ${confirmVariant === 'danger' ? 'text-red-600' : 'text-blue-600'}`} />
                </div>
                <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
              </div>
              <p className="text-sm text-gray-600 mb-6">{message}</p>
              <div className="flex gap-3">
                <Button variant="secondary" onClick={onClose} className="flex-1">
                  Отмена
                </Button>
                <Button variant={confirmVariant} onClick={onConfirm} className="flex-1" isLoading={isLoading}>
                  {confirmLabel}
                </Button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
