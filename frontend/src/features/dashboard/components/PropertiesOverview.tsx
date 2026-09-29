import { motion } from 'framer-motion';
import { Building2 } from 'lucide-react';
import { Card } from '@/shared/ui/Card';
import type { PropertyOverviewItem } from '@/entities/dashboard';

const statusLabels: Record<string, string> = { active: 'Активен', overdue: 'Просрочка' };
const statusColors: Record<string, string> = { active: 'bg-green-100 text-green-700', overdue: 'bg-red-100 text-red-700' };

interface PropertiesOverviewProps {
  data: PropertyOverviewItem[];
}

export function PropertiesOverview({ data }: PropertiesOverviewProps) {
  if (!data || data.length < 3) return null;

  return (
    <Card>
      <h2 className="text-lg font-semibold mb-3 flex items-center gap-2"><Building2 className="h-5 w-5" /> Объекты</h2>

      <div className="hidden sm:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-left text-gray-500">
              <th className="py-2 font-medium">Объект</th>
              <th className="py-2 font-medium">Арендатор</th>
              <th className="py-2 font-medium">Статус</th>
              <th className="py-2 font-medium text-right">Доход/мес</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {data.map((p) => (
              <motion.tr key={p.property_id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="transition-colors">
                <td className="py-2 font-medium truncate max-w-[200px]">{p.address}</td>
                <td className="py-2 text-gray-500">{p.tenant_name || <span className="text-gray-300">—</span>}</td>
                <td className="py-2">
                  {p.contract_status ? (
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[p.contract_status]}`}>{statusLabels[p.contract_status]}</span>
                  ) : <span className="text-gray-300">—</span>}
                </td>
                <td className="py-2 text-right font-medium">
                  {Number(p.monthly_income).toLocaleString('ru-RU')} ₽
                  {p.income_is_forecast ? (
                    <span className="ml-1 text-[11px] font-normal text-amber-600">прогноз</span>
                  ) : null}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="sm:hidden space-y-2">
        {data.map((p) => (
          <div key={p.property_id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
            <div>
              <p className="text-sm font-medium">{p.address}</p>
              <p className="text-xs text-gray-400">{p.tenant_name || 'Свободен'}</p>
            </div>
            <span className="text-sm font-semibold">{Number(p.monthly_income).toLocaleString('ru-RU')} ₽</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
