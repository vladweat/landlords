import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { Download } from 'lucide-react';
import { invoicesApi } from '@/features/invoices/api';
import { formatDate } from '@/shared/lib/utils';
import { FullPageLoader } from '@/shared/ui/FullPageLoader';

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

export default function InvoicePublicPage() {
  const { token = '' } = useParams<{ token: string }>();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['public-invoice', token],
    queryFn: () => invoicesApi.getPublic(token),
    enabled: Boolean(token),
    retry: false,
  });

  if (isLoading) return <FullPageLoader />;

  if (isError || !data) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md text-center">
          <h1 className="text-xl font-semibold text-gray-900">Квитанция не найдена</h1>
          <p className="mt-2 text-sm text-gray-500">
            Ссылка недействительна или устарела. Обратитесь к арендодателю.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-10">
      <div className="mx-auto max-w-lg">
        <p className="text-sm font-medium uppercase tracking-wide text-gray-500">Квитанция</p>
        <h1 className="mt-1 text-2xl font-semibold text-gray-900">{data.landlord_name}</h1>
        <p className="mt-1 text-sm text-gray-600">{data.property_address}</p>

        <div className="mt-8 space-y-4 border-t border-gray-200 pt-6">
          <div className="flex justify-between gap-4 text-sm">
            <span className="text-gray-500">Арендатор</span>
            <span className="text-right font-medium text-gray-900">{data.tenant_name}</span>
          </div>
          <div className="flex justify-between gap-4 text-sm">
            <span className="text-gray-500">Период</span>
            <span className="text-right text-gray-900">
              {formatDate(data.period_start)} — {formatDate(data.period_end)}
            </span>
          </div>
          <div className="flex justify-between gap-4 text-sm">
            <span className="text-gray-500">Срок оплаты</span>
            <span className="text-right text-gray-900">{formatDate(data.due_date)}</span>
          </div>
          <div className="flex justify-between gap-4 text-sm">
            <span className="text-gray-500">Статус</span>
            <span className="text-right font-medium text-gray-900">
              {statusLabels[data.status] || data.status}
            </span>
          </div>
        </div>

        <div className="mt-8 rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-100">
          <p className="text-sm text-gray-500">К оплате</p>
          <p className="mt-1 text-3xl font-semibold tabular-nums text-gray-900">
            {money(data.amount_remaining, data.currency)}
          </p>
          <p className="mt-2 text-xs text-gray-400 tabular-nums">
            Начислено {money(data.amount, data.currency)}
            {Number(data.amount_paid) > 0
              ? ` · оплачено ${money(data.amount_paid, data.currency)}`
              : ''}
          </p>
        </div>

        <div className="mt-6">
          <h2 className="text-sm font-medium text-gray-900">Реквизиты для оплаты</h2>
          <p className="mt-2 whitespace-pre-wrap text-sm text-gray-700">
            {data.payment_details?.trim() || 'Реквизиты не указаны арендодателем.'}
          </p>
        </div>

        <a
          href={invoicesApi.publicPdfUrl(token)}
          className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Download className="h-4 w-4" />
          Скачать PDF
        </a>

        <p className="mt-8 text-center text-xs text-gray-400">
          <Link to="/login" className="hover:text-gray-600">
            Landlords CRM
          </Link>
        </p>
      </div>
    </div>
  );
}
