import { useMemo, useState } from 'react';
import { FileSpreadsheet, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { showError } from '@/shared/lib/toast';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { Card } from '@/shared/ui/Card';
import { reportsApi, type ReportFormat } from '@/features/reports/api';

function defaultStart(): string {
  const d = new Date();
  return `${d.getFullYear()}-01-01`;
}

function defaultEnd(): string {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${m}-${day}`;
}

export default function ReportsPage() {
  const [startDate, setStartDate] = useState(defaultStart);
  const [endDate, setEndDate] = useState(defaultEnd);
  const [loading, setLoading] = useState<ReportFormat | null>(null);

  const invalid = useMemo(
    () => !startDate || !endDate || endDate < startDate,
    [startDate, endDate],
  );

  const handleExport = async (format: ReportFormat) => {
    if (invalid) {
      toast.error('Проверьте период: дата окончания не раньше начала');
      return;
    }
    setLoading(format);
    try {
      await reportsApi.export({
        start_date: startDate,
        end_date: endDate,
        format,
      });
      toast.success(format === 'xlsx' ? 'XLSX скачан' : 'CSV скачан');
    } catch (error) {
      showError(error, 'Ошибка экспорта');
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Отчёты</h1>
        <p className="mt-1 text-sm text-gray-500">
          Экспорт платежей, начислений и расходов за период для налоговой и бухгалтерии
        </p>
      </div>

      <Card>
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-gray-900">Период</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="С"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
            <Input
              label="По"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
          {invalid && (
            <p className="text-sm text-red-600">Дата окончания не может быть раньше даты начала</p>
          )}
          <div className="flex flex-wrap gap-3 pt-2">
            <Button
              onClick={() => void handleExport('xlsx')}
              disabled={invalid}
              isLoading={loading === 'xlsx'}
              leftIcon={<FileSpreadsheet className="h-4 w-4" />}
            >
              Скачать XLSX
            </Button>
            <Button
              variant="secondary"
              onClick={() => void handleExport('csv')}
              disabled={invalid}
              isLoading={loading === 'csv'}
              leftIcon={<FileText className="h-4 w-4" />}
            >
              Скачать CSV
            </Button>
          </div>
          <p className="text-xs text-gray-500">
            XLSX содержит листы: Платежи, Начисления, Расходы, Сводка. CSV — плоский файл с колонкой
            type.
          </p>
        </div>
      </Card>
    </div>
  );
}
