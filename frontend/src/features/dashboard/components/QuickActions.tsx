import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Building2, CalendarDays, FileText, Wallet, type LucideIcon } from 'lucide-react';
import { useCan } from '@/features/auth/permissions';
import { PropertyModal } from '@/pages/properties/PropertyModal';
import { ContractModal } from '@/pages/contracts/ContractModal';
import { PaymentModal } from '@/pages/payments/PaymentModal';
import { cn } from '@/shared/lib/utils';

interface ActionButtonProps {
  label: string;
  icon: LucideIcon;
  onClick?: () => void;
  to?: string;
  className?: string;
}

function ActionButton({ label, icon: Icon, onClick, to, className }: ActionButtonProps) {
  const classes = cn(
    'inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:border-gray-300 hover:bg-gray-50',
    className,
  );

  if (to) {
    return (
      <Link to={to} className={classes}>
        <Icon className="h-4 w-4 text-blue-600" />
        {label}
      </Link>
    );
  }

  return (
    <button type="button" onClick={onClick} className={classes}>
      <Icon className="h-4 w-4 text-blue-600" />
      {label}
    </button>
  );
}

/** Компактные CTA для старта основных сценариев с учётом RBAC. */
export function QuickActions() {
  const canWriteProperties = useCan('write_properties');
  const canWriteContracts = useCan('write_contracts');
  const canWritePayments = useCan('write_payments');
  const [propertyOpen, setPropertyOpen] = useState(false);
  const [contractOpen, setContractOpen] = useState(false);
  const [paymentOpen, setPaymentOpen] = useState(false);

  return (
    <>
      <div className="flex flex-wrap gap-2">
        {canWriteProperties && (
          <ActionButton
            label="Добавить объект"
            icon={Building2}
            onClick={() => setPropertyOpen(true)}
          />
        )}
        {canWriteContracts && (
          <ActionButton
            label="Создать договор"
            icon={FileText}
            onClick={() => setContractOpen(true)}
          />
        )}
        {canWritePayments && (
          <ActionButton
            label="Записать платёж"
            icon={Wallet}
            onClick={() => setPaymentOpen(true)}
          />
        )}
        <ActionButton label="Открыть календарь" icon={CalendarDays} to="/calendar" />
      </div>

      {canWriteProperties && (
        <PropertyModal
          isOpen={propertyOpen}
          onClose={() => setPropertyOpen(false)}
          property={null}
        />
      )}
      {canWriteContracts && (
        <ContractModal
          isOpen={contractOpen}
          onClose={() => setContractOpen(false)}
          contract={null}
        />
      )}
      {canWritePayments && (
        <PaymentModal isOpen={paymentOpen} onClose={() => setPaymentOpen(false)} />
      )}
    </>
  );
}
