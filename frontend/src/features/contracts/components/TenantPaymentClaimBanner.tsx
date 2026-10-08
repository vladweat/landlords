import { Button } from '@/shared/ui/Button';
import { formatContractMoney } from '@/features/contracts/lib/display';

interface Claim {
  id: string;
  amount?: string | null;
  note?: string | null;
}

interface TenantPaymentClaimBannerProps {
  claim: Claim;
  currency: string;
  canConfirm: boolean;
  isDismissing: boolean;
  isConfirming: boolean;
  onDismiss: () => void;
  onConfirm: () => void;
}

export function TenantPaymentClaimBanner({
  claim,
  currency,
  canConfirm,
  isDismissing,
  isConfirming,
  onDismiss,
  onConfirm,
}: TenantPaymentClaimBannerProps) {
  return (
    <div className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-medium text-teal-900">Арендатор сообщил об оплате</p>
          <p className="mt-0.5 text-sm text-teal-800">
            {claim.amount ? formatContractMoney(claim.amount, currency) : 'Сумма не указана'}
            {claim.note ? ` · ${claim.note}` : ''}
          </p>
        </div>
        {canConfirm && (
          <div className="flex flex-wrap gap-2 shrink-0">
            <Button size="sm" variant="secondary" isLoading={isDismissing} onClick={onDismiss}>
              Отклонить
            </Button>
            <Button size="sm" isLoading={isConfirming} onClick={onConfirm}>
              Подтвердить платёж
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
