import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Building2, CalendarDays, FileText, Wallet, type LucideIcon } from 'lucide-react';
import { useCan } from '@/features/auth/permissions';
import { PropertyModal } from '@/features/properties/components/PropertyModal';
import { ContractModal } from '@/features/contracts/components/ContractModal';
import { PaymentModal } from '@/features/payments/components/PaymentModal';
import { cn } from '@/shared/lib/utils';

interface ActionButtonProps {
  label: string;
  shortLabel?: string;
  icon: LucideIcon;
  onClick?: () => void;
  to?: string;
  compact?: boolean;
}

function ActionButton({
  label,
  shortLabel,
  icon: Icon,
  onClick,
  to,
  compact,
}: ActionButtonProps) {
  const classes = cn(
    'inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white text-sm font-medium text-gray-700 transition-colors hover:border-gray-300 hover:bg-gray-50',
    compact ? 'px-2.5 py-1.5' : 'px-3 py-2 shadow-sm',
  );
  const text = compact && shortLabel ? shortLabel : label;

  if (to) {
    return (
      <Link to={to} className={classes} title={label}>
        <Icon className="h-3.5 w-3.5 text-blue-600" />
        {text}
      </Link>
    );
  }

  return (
    <button type="button" onClick={onClick} className={classes} title={label}>
      <Icon className="h-3.5 w-3.5 text-blue-600" />
      {text}
    </button>
  );
}

interface QuickActionsProps {
  compact?: boolean;
}

/** Компактные CTA для старта основных сценариев с учётом RBAC. */
export function QuickActions({ compact = false }: QuickActionsProps) {
  const canWriteProperties = useCan('write_properties');
  const canWriteContracts = useCan('write_contracts');
  const canWritePayments = useCan('write_payments');
  const [propertyOpen, setPropertyOpen] = useState(false);
  const [contractOpen, setContractOpen] = useState(false);
  const [paymentOpen, setPaymentOpen] = useState(false);

  return (
    <>
      <div className="flex flex-wrap gap-1.5">
        {canWriteProperties && (
          <ActionButton
            label="Добавить объект"
            shortLabel="Объект"
            icon={Building2}
            compact={compact}
            onClick={() => setPropertyOpen(true)}
          />
        )}
        {canWriteContracts && (
          <ActionButton
            label="Создать договор"
            shortLabel="Договор"
            icon={FileText}
            compact={compact}
            onClick={() => setContractOpen(true)}
          />
        )}
        {canWritePayments && (
          <ActionButton
            label="Записать платёж"
            shortLabel="Платёж"
            icon={Wallet}
            compact={compact}
            onClick={() => setPaymentOpen(true)}
          />
        )}
        <ActionButton
          label="Открыть календарь"
          shortLabel="Календарь"
          icon={CalendarDays}
          compact={compact}
          to="/calendar"
        />
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
