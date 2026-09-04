import { useParams, useNavigate, Link } from 'react-router-dom';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Plus, Trash2, Pencil, Wallet } from 'lucide-react';
import { toast } from 'sonner';
import { showError } from '@/shared/lib/toast';
import { formatDate } from '@/shared/lib/utils';
import { propertiesApi } from '@/features/properties/api';
import { expensesApi } from '@/features/expenses/api';
import type { PropertyExpense } from '@/entities/expense';
import { EXPENSE_CATEGORY_LABELS } from '@/entities/expense';
import { Card } from '@/shared/ui/Card';
import { Button } from '@/shared/ui/Button';
import { Skeleton, TableSkeleton } from '@/shared/ui/Skeleton';
import { EmptyState } from '@/shared/ui/EmptyState';
import { ActionMenu } from '@/shared/ui/ActionMenu';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { ROIBadge } from '@/features/properties/components/ROIBadge';
import { ExpenseModal } from '@/pages/expenses/ExpenseModal';
import { PropertyModal } from './PropertyModal';
import { AttachmentsSection } from '@/features/documents/components/AttachmentsSection';
import { useCan } from '@/features/auth/permissions';

const typeLabels: Record<string, string> = {
  apartment: 'Квартира',
  house: 'Дом',
  commercial: 'Коммерческая',
};

const contractStatusLabels: Record<string, string> = {
  active: 'Активен',
  overdue: 'Просрочен',
};

const contractStatusDots: Record<string, string> = {
  active: 'bg-emerald-500',
  overdue: 'bg-red-500',
};

export default function PropertyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const canWriteProperty = useCan('write_properties');
  const canWriteExpenses = useCan('write_expenses');
  const [isExpenseModalOpen, setIsExpenseModalOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [deleting, setDeleting] = useState<PropertyExpense | null>(null);

  const { data: property, isLoading } = useQuery({
    queryKey: ['property', id],
    queryFn: () => propertiesApi.getById(id!),
    enabled: !!id,
  });

  const { data: expenses, isLoading: expensesLoading } = useQuery({
    queryKey: ['expenses', id],
    queryFn: () => expensesApi.getAll(id!),
    enabled: !!id,
  });

  const deleteMutation = useMutation({
    mutationFn: expensesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
      queryClient.invalidateQueries({ queryKey: ['properties'] });
      queryClient.invalidateQueries({ queryKey: ['property', id] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      setDeleting(null);
      toast.success('Расход удалён');
    },
    onError: (error) => showError(error, 'Ошибка удаления'),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card>
            <Skeleton className="h-5 w-24 mb-4" />
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-4 w-full mb-2" />
            ))}
          </Card>
          <Card>
            <Skeleton className="h-5 w-24 mb-4" />
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-4 w-full mb-2" />
            ))}
          </Card>
        </div>
      </div>
    );
  }

  if (!property) return <p className="text-red-500">Объект не найден</p>;

  const roi = property.roi;
  const activeContract = property.active_contract;

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate('/properties')}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900"
      >
        <ArrowLeft className="h-4 w-4" /> Назад
      </button>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">{property.address}</h1>
        {canWriteProperty && (
          <Button
            variant="secondary"
            leftIcon={<Pencil className="h-4 w-4" />}
            onClick={() => setIsEditOpen(true)}
          >
            Редактировать
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="text-lg font-medium text-gray-800 mb-3">Детали</h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Тип</span>
              <span>{typeLabels[property.type] || property.type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Площадь</span>
              <span>{property.size_m2} м²</span>
            </div>
            {property.purchase_price && Number(property.purchase_price) > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-500">Стоимость покупки</span>
                <span>{Number(property.purchase_price).toLocaleString('ru-RU')} ₽</span>
              </div>
            )}
            {activeContract ? (
              <div className="flex justify-between gap-4 pt-2 border-t border-gray-100">
                <span className="text-gray-500 shrink-0">Договор</span>
                <Link
                  to={`/contracts/${activeContract.id}`}
                  className="inline-flex items-center gap-2 text-right text-blue-600 hover:text-blue-800"
                >
                  <span
                    className={`w-2 h-2 rounded-full ${contractStatusDots[activeContract.status] || 'bg-gray-400'}`}
                  />
                  {activeContract.tenant_name}
                  {' · '}
                  {contractStatusLabels[activeContract.status] || activeContract.status}
                </Link>
              </div>
            ) : (
              <div className="flex justify-between pt-2 border-t border-gray-100">
                <span className="text-gray-500">Договор</span>
                <span className="inline-flex items-center gap-2 text-gray-500">
                  <span className="w-2 h-2 rounded-full bg-gray-300" />
                  Свободен
                </span>
              </div>
            )}
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-medium text-gray-800">Финансы</h2>
            <ROIBadge roi={roi?.roi ?? null} />
          </div>
          {roi ? (
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">
                  Годовой доход
                  {roi.income_is_forecast ? (
                    <span className="ml-1 text-xs text-amber-600">(прогноз)</span>
                  ) : null}
                </span>
                <span>{Number(roi.annual_income).toLocaleString('ru-RU')} ₽</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Годовые расходы</span>
                <span>{Number(roi.annual_expenses).toLocaleString('ru-RU')} ₽</span>
              </div>
              <div className="border-t pt-2 flex justify-between">
                <span className="font-medium">Прибыль</span>
                <span
                  className={`font-semibold ${Number(roi.annual_profit) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}
                >
                  {Number(roi.annual_profit).toLocaleString('ru-RU')} ₽
                </span>
              </div>
              {roi.payback_years != null && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Окупаемость</span>
                  <span>{roi.payback_years.toFixed(1)} лет</span>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-500">Нет данных для расчёта</p>
          )}
        </Card>
      </div>

      <Card>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-medium text-gray-800">Расходы</h2>
          {canWriteExpenses && (
            <Button
              size="sm"
              leftIcon={<Plus className="h-4 w-4" />}
              onClick={() => setIsExpenseModalOpen(true)}
            >
              Добавить
            </Button>
          )}
        </div>

        {expensesLoading ? (
          <TableSkeleton rows={4} cols={4} />
        ) : !expenses?.length ? (
          <EmptyState
            icon={Wallet}
            title="Нет расходов"
            description="Учитывайте ЖКХ, ремонт, налоги и комиссию — ROI станет точнее"
            
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-wide text-gray-500 border-b">
                  <th className="py-2 text-left font-medium">Категория</th>
                  <th className="py-2 text-left font-medium">Сумма</th>
                  <th className="py-2 text-left font-medium">Дата</th>
                  <th className="py-2 text-left font-medium hidden sm:table-cell">Примечание</th>
                  <th className="py-2 text-right font-medium w-10"></th>
                </tr>
              </thead>
              <tbody>
                <AnimatePresence>
                  {expenses.map((e) => (
                    <motion.tr
                      key={e.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="border-b last:border-0"
                    >
                      <td className="py-2">{EXPENSE_CATEGORY_LABELS[e.category] || e.category}</td>
                      <td className="py-2 font-medium">
                        {Number(e.amount).toLocaleString('ru-RU')} {e.currency}
                      </td>
                      <td className="py-2 text-gray-600">{formatDate(e.date_incurred)}</td>
                      <td className="py-2 text-gray-500 hidden sm:table-cell">{e.note || '—'}</td>
                      <td className="py-2 text-right">
                        {canWriteExpenses && (
                          <ActionMenu
                            items={[
                              {
                                label: 'Удалить',
                                icon: <Trash2 className="h-4 w-4" />,
                                danger: true,
                                onClick: () => setDeleting(e),
                              },
                            ]}
                          />
                        )}
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <AttachmentsSection parentType="property" parentId={property.id} />

      {canWriteExpenses && (
        <ExpenseModal
          isOpen={isExpenseModalOpen}
          onClose={() => setIsExpenseModalOpen(false)}
          defaultPropertyId={property.id}
        />
      )}
      {canWriteProperty && (
        <PropertyModal
          isOpen={isEditOpen}
          onClose={() => setIsEditOpen(false)}
          property={property}
        />
      )}
      <ConfirmDialog
        isOpen={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
        title="Удалить расход?"
        message={`Удалить расход на ${deleting ? Number(deleting.amount).toLocaleString('ru-RU') : ''} ${deleting?.currency || ''}?`}
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
}
