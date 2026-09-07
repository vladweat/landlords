import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileText, Pencil, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { contractTemplatesApi } from '../api';
import type { ContractTemplate, PropertyType } from '@/entities/contractTemplate';
import { PROPERTY_TYPE_LABELS } from '@/entities/contractTemplate';
import { useCan } from '@/features/auth/permissions';
import { showError } from '@/shared/lib/toast';
import { Button } from '@/shared/ui/Button';
import { Card } from '@/shared/ui/Card';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { Input } from '@/shared/ui/Input';

const emptyForm = {
  name: '',
  title: '',
  body: '',
  property_type: '' as '' | PropertyType,
  is_default: false,
};

export function ContractTemplatesSection() {
  const canWrite = useCan('write_contracts');
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<ContractTemplate | null>(null);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<ContractTemplate | null>(null);
  const [form, setForm] = useState(emptyForm);

  const { data, isLoading } = useQuery({
    queryKey: ['contract-templates'],
    queryFn: contractTemplatesApi.list,
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['contract-templates'] });
  };

  const createMutation = useMutation({
    mutationFn: contractTemplatesApi.create,
    onSuccess: () => {
      invalidate();
      setCreating(false);
      setForm(emptyForm);
      toast.success('Шаблон создан');
    },
    onError: (e) => showError(e, 'Ошибка создания'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: typeof form }) =>
      contractTemplatesApi.update(id, {
        name: payload.name,
        title: payload.title,
        body: payload.body,
        property_type: payload.property_type || null,
        is_default: payload.is_default,
      }),
    onSuccess: () => {
      invalidate();
      setEditing(null);
      setForm(emptyForm);
      toast.success('Шаблон сохранён');
    },
    onError: (e) => showError(e, 'Ошибка сохранения'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => contractTemplatesApi.remove(id),
    onSuccess: () => {
      invalidate();
      setDeleting(null);
      toast.success('Шаблон удалён');
    },
    onError: (e) => showError(e, 'Ошибка удаления'),
  });

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setCreating(true);
  };

  const openEdit = (tpl: ContractTemplate) => {
    setCreating(false);
    setEditing(tpl);
    setForm({
      name: tpl.name,
      title: tpl.title,
      body: tpl.body,
      property_type: (tpl.property_type || '') as '' | PropertyType,
      is_default: tpl.is_default,
    });
  };

  const submit = () => {
    if (!form.name.trim() || !form.title.trim() || !form.body.trim()) {
      toast.error('Заполните название, заголовок и текст');
      return;
    }
    const payload = {
      name: form.name.trim(),
      title: form.title.trim(),
      body: form.body,
      property_type: (form.property_type || null) as PropertyType | null,
      is_default: form.is_default,
    };
    if (editing) {
      updateMutation.mutate({ id: editing.id, payload: form });
    } else {
      createMutation.mutate(payload);
    }
  };

  const showForm = creating || !!editing;
  const placeholders = data?.placeholders ?? [];

  return (
    <Card>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-lg font-medium text-gray-800">
          <FileText className="h-5 w-5" /> Шаблоны договоров
        </h2>
        {canWrite && !showForm && (
          <Button size="sm" onClick={openCreate} leftIcon={<Plus className="h-4 w-4" />}>
            Добавить
          </Button>
        )}
      </div>

      <p className="mb-4 text-sm text-gray-500">
        Текст с плейсхолдерами вида {'{{ tenant_name }}'}. Несколько шаблонов — под типы объектов.
      </p>

      {isLoading ? (
        <p className="text-sm text-gray-500">Загрузка…</p>
      ) : (
        <ul className="mb-4 divide-y divide-gray-100 rounded-lg border border-gray-100">
          {(data?.items ?? []).map((tpl) => (
            <li key={tpl.id} className="flex items-start justify-between gap-3 px-3 py-3">
              <div className="min-w-0">
                <div className="font-medium text-gray-900">{tpl.name}</div>
                <div className="text-xs text-gray-500">
                  {PROPERTY_TYPE_LABELS[tpl.property_type || 'any']}
                  {tpl.is_default ? ' · по умолчанию' : ''}
                </div>
                <div className="mt-1 truncate text-xs text-gray-400">{tpl.title}</div>
              </div>
              {canWrite && (
                <div className="flex gap-1">
                  <button
                    type="button"
                    className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
                    onClick={() => openEdit(tpl)}
                    title="Редактировать"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
                    onClick={() => setDeleting(tpl)}
                    title="Удалить"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {showForm && canWrite && (
        <div className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <Input
            label="Название"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          />
          <Input
            label="Заголовок PDF"
            value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
          />
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Тип объекта</label>
            <select
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              value={form.property_type}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  property_type: e.target.value as '' | PropertyType,
                }))
              }
            >
              <option value="">Все типы</option>
              <option value="apartment">Квартира</option>
              <option value="house">Дом</option>
              <option value="room">Комната</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={form.is_default}
              onChange={(e) => setForm((f) => ({ ...f, is_default: e.target.checked }))}
            />
            По умолчанию для этого типа
          </label>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Текст шаблона</label>
            <textarea
              rows={12}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-xs focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.body}
              onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
            />
            {placeholders.length > 0 && (
              <p className="mt-1 text-xs text-gray-500">
                Плейсхолдеры: {placeholders.map((p) => `{{ ${p} }}`).join(', ')}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={submit}
              isLoading={createMutation.isPending || updateMutation.isPending}
            >
              {editing ? 'Сохранить' : 'Создать'}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                setCreating(false);
                setEditing(null);
                setForm(emptyForm);
              }}
            >
              Отмена
            </Button>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
        title="Удалить шаблон?"
        message={`Шаблон «${deleting?.name ?? ''}» будет удалён.`}
        isLoading={deleteMutation.isPending}
      />
    </Card>
  );
}
