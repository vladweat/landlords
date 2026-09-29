import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { ForecastMonth } from '@/entities/dashboard';

const monthNames: Record<string, string> = {
  '01': 'янв', '02': 'фев', '03': 'мар', '04': 'апр', '05': 'май', '06': 'июн',
  '07': 'июл', '08': 'авг', '09': 'сен', '10': 'окт', '11': 'ноя', '12': 'дек',
};

interface ForecastChartProps {
  months: ForecastMonth[];
}

export function ForecastChart({ months }: ForecastChartProps) {
  if (months.length === 0) return null;

  const now = new Date();
  const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

  const data = months.map((m) => ({
    month: monthNames[m.month.slice(5, 7)] || m.month,
    income: m.expected_income,
    isEnding: m.contracts_ending > 0,
    isPast: m.month < currentMonth,
    isCurrent: m.month === currentMonth,
    isFuture: m.month > currentMonth,
  }));

  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={data} barSize={28} barGap={6}>
        <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={45} tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} />
        <Tooltip
          formatter={(value) => [`${Number(value ?? 0).toLocaleString('ru-RU')} ₽`, 'Доход']}
          labelFormatter={(label) => `${String(label)} 2026`}
          contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 2px 8px rgba(0,0,0,0.04)', fontSize: '12px', padding: '6px 10px' }}
        />
        <Bar dataKey="income" radius={[6, 6, 0, 0]}>
          {data.map((entry, index) => {
            let fill = '#93c5fd'; // будущий
            if (entry.isEnding) fill = '#f59e0b';
            else if (entry.isCurrent) fill = '#2563eb';
            else if (entry.isPast) fill = '#bfdbfe';
            return <Cell key={index} fill={fill} />;
          })}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
