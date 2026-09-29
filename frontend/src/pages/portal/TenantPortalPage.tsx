import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';
import { portalApi } from '@/features/portal/api';
import { formatDate } from '@/shared/lib/utils';
import { showError } from '@/shared/lib/toast';
import { FullPageLoader } from '@/shared/ui/FullPageLoader';
import { Button } from '@/shared/ui/Button';

const statusLabels: Record<string, string> = {
  paid: 'Оплачено',
  overdue: 'Просрочено',
  partially_paid: 'Частично оплачено',
  pending: 'Ожидает оплаты',
};

function money(value: string | number, currency: string): string {
  const n = typeof value === 'string' ? Number(value) : value;
  const suffix = currency === 'RUB' ? '₽' : currency;
  return `${n.toLocaleString('ru-RU')} ${suffix}`;
}

export default function TenantPortalPage() {
  const { token = '' } = useParams<{ token: string }>();
  const queryClient = useQueryClient();
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['public-portal', token],
    queryFn: () => portalApi.getPublic(token),
    enabled: Boolean(token),
    retry: false,
  });

  useEffect(() => {
    if (!data) return;
    const outstanding = Math.max(0, Number(data.outstanding_balance));
    if (outstanding > 0) {
      setAmount(String(outstanding));
    }
  }, [data]);

  const claimMutation = useMutation({
    mutationFn: () =>
      portalApi.createClaim(token, {
        amount: amount.trim(),
        note: note.trim() || undefined,
      }),
    onSuccess: () => {
      setNote('');
      queryClient.invalidateQueries({ queryKey: ['public-portal', token] });
    },
    onError: (error) => showError(error, 'Не удалось отправить заявку'),
  });

  if (isLoading) return <FullPageLoader />;

  if (isError || !data) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md text-center">
          <h1 className="text-xl font-semibold text-gray-900">Ссылка недействительна</h1>
          <p className="mt-2 text-sm text-gray-500">
            Обратитесь к арендодателю за новой ссылкой на кабинет.
          </p>
        </div>
      </div>
    );
  }

  const hasPending = Boolean(data.pending_claim);
  const outstanding = Number(data.outstanding_balance);
  const amountNum = Number(amount.replace(',', '.'));
  const canSubmit =
    !hasPending &&
    !claimMutation.isPending &&
    Number.isFinite(amountNum) &&
    amountNum > 0;

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-10">
      <div className="mx-auto max-w-lg">
        <p className="text-sm font-medium uppercase tracking-wide text-gray-500">Кабинет арендатора</p>
        <h1 className="mt-1 text-2xl font-semibold text-gray-900">{data.landlord_name}</h1>
        <p className="mt-1 text-sm text-gray-600">{data.property_address}</p>
        <p className="mt-1 text-sm text-gray-500">{data.tenant_name}</p>

        <div className="mt-8 rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-100">
          <p className="text-sm text-gray-500">Баланс</p>
          <p className="mt-1 text-3xl font-semibold tabular-nums text-gray-900">
            {money(data.outstanding_balance, data.currency)}
          </p>
          <p className="mt-2 text-xs text-gray-400 tabular-nums">
            Начислено {money(data.total_expected, data.currency)}
            {Number(data.total_paid) > 0
              ? ` · оплачено ${money(data.total_paid, data.currency)}`
              : ''}
          </p>
          {outstanding > 0 ? (
            <p className="mt-1 text-xs text-amber-700">К оплате арендодателю</p>
          ) : outstanding < 0 ? (
            <p className="mt-1 text-xs text-emerald-700">Аванс (переплата)</p>
          ) : (
            <p className="mt-1 text-xs text-emerald-700">Всё оплачено</p>
          )}
        </div>

        {hasPending && (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Заявка об оплате
            {data.pending_claim?.amount
              ? ` на ${money(data.pending_claim.amount, data.currency)}`
              : ''}{' '}
            отправлена. Арендодатель подтвердит поступление денег.
          </div>
        )}

        {data.open_charges.length > 0 && (
          <div className="mt-8">
            <h2 className="text-sm font-medium text-gray-900">Квитанции</h2>
            <ul className="mt-3 space-y-2">
              {data.open_charges.map((charge) => (
                <li
                  key={charge.charge_id}
                  className="flex items-center justify-between gap-3 rounded-lg bg-white px-4 py-3 text-sm ring-1 ring-gray-100"
                >
                  <div className="min-w-0">
                    <p className="font-medium text-gray-900 tabular-nums">
                      {money(charge.amount_remaining, charge.currency)}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatDate(charge.period_start)} — {formatDate(charge.period_end)} ·{' '}
                      {statusLabels[charge.status] || charge.status}
                    </p>
                  </div>
                  {charge.invoice_url && (
                    <a
                      href={charge.invoice_url}
                      className="inline-flex shrink-0 items-center gap-1 text-blue-600 hover:text-blue-800"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      Открыть
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-8">
          <h2 className="text-sm font-medium text-gray-900">Реквизиты для оплаты</h2>
          <p className="mt-2 whitespace-pre-wrap text-sm text-gray-700">
            {data.payment_details?.trim() || 'Реквизиты не указаны арендодателем.'}
          </p>
        </div>

        <div className="mt-6 space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-900" htmlFor="claim-amount">
              Сумма оплаты
            </label>
            <input
              id="claim-amount"
              type="text"
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              disabled={hasPending}
              className="mt-1.5 w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm tabular-nums text-gray-900 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
              placeholder="0"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-900" htmlFor="claim-note">
              Комментарий <span className="font-normal text-gray-400">(необязательно)</span>
            </label>
            <input
              id="claim-note"
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={hasPending}
              maxLength={500}
              className="mt-1.5 w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-900 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
              placeholder="Например: перевод с карты …"
            />
          </div>
          <Button
            className="w-full"
            disabled={!canSubmit}
            isLoading={claimMutation.isPending}
            onClick={() => claimMutation.mutate()}
          >
            {hasPending ? 'Заявка уже отправлена' : 'Я оплатил'}
          </Button>
          <p className="text-center text-xs text-gray-400">
            Сообщит арендодателю — платёж в учёте появится после подтверждения.
          </p>
        </div>

        {data.history.length > 0 && (
          <div className="mt-10">
            <h2 className="text-sm font-medium text-gray-900">История</h2>
            <ul className="mt-3 divide-y divide-gray-100 rounded-xl bg-white ring-1 ring-gray-100">
              {data.history.map((line, idx) => (
                <li key={`${line.date}-${line.type}-${idx}`} className="flex justify-between gap-3 px-4 py-3 text-sm">
                  <div className="min-w-0">
                    <p className="text-gray-900">{line.description}</p>
                    <p className="text-xs text-gray-400">{formatDate(line.date)}</p>
                  </div>
                  <p
                    className={`shrink-0 tabular-nums font-medium ${
                      line.type === 'payment' ? 'text-emerald-700' : 'text-gray-900'
                    }`}
                  >
                    {line.type === 'payment' ? '−' : '+'}
                    {money(Math.abs(Number(line.amount)), data.currency)}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        )}

        <p className="mt-8 text-center text-xs text-gray-400">
          <Link to="/login" className="hover:text-gray-600">
            Landlords CRM
          </Link>
        </p>
      </div>
    </div>
  );
}
