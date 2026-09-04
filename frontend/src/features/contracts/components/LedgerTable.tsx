import { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { LedgerLine } from '@/entities/contract';
import { formatDate } from '@/shared/lib/utils';
import { DetailTable, DetailTd, DetailTh } from '@/shared/ui/DetailTable';

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

type DisplayRow =
  | { kind: 'single'; line: LedgerLine; key: string }
  | { kind: 'payment_group'; lines: LedgerLine[]; key: string };

function formatMoney(amount: number, currency: string): string {
  const suffix = currency === 'RUB' ? '₽' : currency;
  return `${Math.abs(amount).toLocaleString('ru-RU')} ${suffix}`;
}

function operationLabel(line: LedgerLine): string {
  if (line.type === 'charge') {
    const match = line.description.match(
      /период\s+(\d{4}-\d{2}-\d{2})\s*[—\-]\s*(\d{4}-\d{2}-\d{2})/i,
    );
    if (match) {
      return `Начислено · ${formatDate(match[1])} — ${formatDate(match[2])}`;
    }
    const fallback = line.description.match(/период\s+(.+)/i);
    return fallback ? `Начислено · ${fallback[1]}` : 'Начислено';
  }
  const match = line.description.match(/\(([^)]+)\)/);
  const method = match?.[1] ? METHOD_LABELS[match[1]] || match[1] : null;
  return method ? `Получено · ${method}` : 'Получено';
}

function balanceLabel(balance: number, currency: string): { text: string; className: string } {
  if (balance > 0) {
    return { text: formatMoney(balance, currency), className: 'text-amber-600' };
  }
  if (balance < 0) {
    return { text: `аванс ${formatMoney(balance, currency)}`, className: 'text-blue-600' };
  }
  return { text: formatMoney(0, currency), className: 'text-emerald-600' };
}

function groupLedgerLines(ordered: LedgerLine[]): DisplayRow[] {
  const rows: DisplayRow[] = [];
  let i = 0;
  while (i < ordered.length) {
    const line = ordered[i];
    if (line.type === 'payment') {
      const group = [line];
      let j = i + 1;
      while (j < ordered.length && ordered[j].type === 'payment' && ordered[j].date === line.date) {
        group.push(ordered[j]);
        j += 1;
      }
      if (group.length > 1) {
        rows.push({ kind: 'payment_group', lines: group, key: `g-${line.date}-${i}` });
        i = j;
        continue;
      }
    }
    rows.push({ kind: 'single', line: line, key: `s-${line.date}-${line.type}-${i}` });
    i += 1;
  }
  return rows;
}

function MobileLedgerCard({
  item,
  currency,
}: {
  item: DisplayRow;
  currency: string;
}) {
  const [open, setOpen] = useState(false);

  if (item.kind === 'payment_group') {
    const { lines } = item;
    const total = lines.reduce((sum, l) => sum + Math.abs(Number(l.amount)), 0);
    const after = balanceLabel(Number(lines[lines.length - 1].balance), currency);
    const head = lines[0];
    return (
      <li className="rounded-xl border border-gray-100 p-4">
        <button type="button" onClick={() => setOpen((v) => !v)} className="w-full text-left">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="text-xs text-gray-500">{formatDate(head.date)}</p>
              <p className="mt-0.5 inline-flex flex-wrap items-center gap-1.5 text-sm font-medium text-gray-900">
                {open ? <ChevronDown className="h-3.5 w-3.5 text-gray-400" /> : <ChevronRight className="h-3.5 w-3.5 text-gray-400" />}
                {operationLabel(head)}
                <span className="rounded-md bg-gray-100 px-1.5 py-0.5 text-[11px] font-medium text-gray-500">
                  {lines.length} части
                </span>
              </p>
            </div>
            <p className="shrink-0 text-sm font-semibold tabular-nums text-emerald-600">
              +{formatMoney(total, currency)}
            </p>
          </div>
          <p className={`mt-2 text-xs tabular-nums ${after.className}`}>после: {after.text}</p>
        </button>
        {open && (
          <ul className="mt-3 space-y-2 border-t border-gray-100 pt-3">
            {lines.map((line, idx) => {
              const partAfter = balanceLabel(Number(line.balance), currency);
              return (
                <li key={`${line.date}-${idx}`} className="flex justify-between gap-2 text-sm">
                  <span className="text-gray-500">часть {idx + 1}</span>
                  <span className="tabular-nums text-emerald-600/80">
                    +{formatMoney(Number(line.amount), currency)}
                  </span>
                  <span className={`tabular-nums ${partAfter.className}`}>{partAfter.text}</span>
                </li>
              );
            })}
          </ul>
        )}
      </li>
    );
  }

  const line = item.line;
  const amount = Number(line.amount);
  const isPayment = line.type === 'payment';
  const after = balanceLabel(Number(line.balance), currency);

  return (
    <li className="rounded-xl border border-gray-100 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs text-gray-500">{formatDate(line.date)}</p>
          <p className="mt-0.5 text-sm font-medium text-gray-900">{operationLabel(line)}</p>
        </div>
        <p
          className={`shrink-0 text-sm font-semibold tabular-nums ${
            isPayment ? 'text-emerald-600' : 'text-gray-900'
          }`}
        >
          {isPayment ? '+' : ''}
          {formatMoney(amount, currency)}
        </p>
      </div>
      <p className={`mt-2 text-xs tabular-nums ${after.className}`}>после: {after.text}</p>
    </li>
  );
}

function PaymentGroupRow({
  lines,
  currency,
}: {
  lines: LedgerLine[];
  currency: string;
}) {
  const [open, setOpen] = useState(false);
  const total = lines.reduce((sum, l) => sum + Math.abs(Number(l.amount)), 0);
  const after = balanceLabel(Number(lines[lines.length - 1].balance), currency);
  const head = lines[0];

  return (
    <>
      <tr className="border-b border-gray-100 last:border-0 transition-colors hover:bg-gray-50/80">
        <DetailTd muted>{formatDate(head.date)}</DetailTd>
        <DetailTd>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="inline-flex items-center gap-1.5 text-left hover:text-blue-700"
          >
            {open ? (
              <ChevronDown className="h-3.5 w-3.5 text-gray-400" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 text-gray-400" />
            )}
            <span className="font-medium text-gray-900">{operationLabel(head)}</span>
            <span className="rounded-md bg-gray-100 px-1.5 py-0.5 text-[11px] font-medium text-gray-500">
              {lines.length} части
            </span>
          </button>
        </DetailTd>
        <DetailTd align="right" mono className="font-medium text-emerald-600">
          +{formatMoney(total, currency)}
        </DetailTd>
        <DetailTd align="right" mono className={`font-medium ${after.className}`}>
          {after.text}
        </DetailTd>
      </tr>
      {open &&
        lines.map((line, idx) => {
          const partAfter = balanceLabel(Number(line.balance), currency);
          return (
            <tr key={`${line.date}-part-${idx}`} className="border-b border-gray-100 last:border-0 bg-gray-50/60">
              <DetailTd muted />
              <DetailTd muted className="text-gray-500">
                часть {idx + 1}
              </DetailTd>
              <DetailTd align="right" mono className="text-emerald-600/80">
                +{formatMoney(Number(line.amount), currency)}
              </DetailTd>
              <DetailTd align="right" mono className={partAfter.className}>
                {partAfter.text}
              </DetailTd>
            </tr>
          );
        })}
    </>
  );
}

export function LedgerTable({ lines, currency }: LedgerTableProps) {
  const ordered = useMemo(() => [...lines].reverse(), [lines]);
  const rows = useMemo(() => groupLedgerLines(ordered), [ordered]);

  return (
    <div className="space-y-3">
      <p className="text-xs text-gray-500 leading-relaxed">
        Справа / ниже — баланс после операции. Разбитый платёж свёрнут — раскройте детали.
      </p>

      <ul className="space-y-3 lg:hidden">
        {rows.map((item) => (
          <MobileLedgerCard key={item.key} item={item} currency={currency} />
        ))}
      </ul>

      <div className="hidden lg:block">
        <DetailTable>
          <thead>
            <tr>
              <DetailTh>Дата</DetailTh>
              <DetailTh>Операция</DetailTh>
              <DetailTh align="right">Сумма</DetailTh>
              <DetailTh align="right">После</DetailTh>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => {
              if (item.kind === 'payment_group') {
                return <PaymentGroupRow key={item.key} lines={item.lines} currency={currency} />;
              }
              const line = item.line;
              const amount = Number(line.amount);
              const isPayment = line.type === 'payment';
              const after = balanceLabel(Number(line.balance), currency);

              return (
                <tr
                  key={item.key}
                  className="border-b border-gray-100 last:border-0 transition-colors hover:bg-gray-50/80"
                >
                  <DetailTd muted>{formatDate(line.date)}</DetailTd>
                  <DetailTd className="font-medium text-gray-900">{operationLabel(line)}</DetailTd>
                  <DetailTd
                    align="right"
                    mono
                    className={`font-medium ${isPayment ? 'text-emerald-600' : 'text-gray-900'}`}
                  >
                    {isPayment ? '+' : ''}
                    {formatMoney(amount, currency)}
                  </DetailTd>
                  <DetailTd align="right" mono className={`font-medium ${after.className}`}>
                    {after.text}
                  </DetailTd>
                </tr>
              );
            })}
          </tbody>
        </DetailTable>
      </div>
    </div>
  );
}
