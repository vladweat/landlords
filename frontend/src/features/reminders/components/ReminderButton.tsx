import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bell, Check, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { remindersApi } from '@/features/reminders/api';
import { showError } from '@/shared/lib/toast';
import { copyToClipboard } from '@/shared/lib/clipboard';

interface ReminderButtonProps {
  chargeId: string;
  chargeStatus: string;
  dueDate: string;
  daysOverdue: number;
}

export function ReminderButton({ chargeId, chargeStatus }: ReminderButtonProps) {
  const queryClient = useQueryClient();

  const { data: reminders = [] } = useQuery({
    queryKey: ['reminders', chargeId],
    queryFn: () => remindersApi.getByCharge(chargeId),
    enabled: chargeStatus === 'overdue',
  });

  const reminderCount = reminders.length;

  const createReminder = useMutation({
    mutationFn: remindersApi.create,
    onSuccess: async (data) => {
      queryClient.invalidateQueries({ queryKey: ['reminders', chargeId] });
      await copyToClipboard(data.message_text);
      
    },
    onError: (error) => showError(error, 'Ошибка отправки'),
  });

  if (chargeStatus !== 'overdue') return null;

  const getReminderType = (): 'first' | 'second' | 'third' => {
    if (reminderCount >= 2) return 'third';
    if (reminderCount >= 1) return 'second';
    return 'first';
  };

  const handleClick = () => {
    createReminder.mutate({
      charge_id: chargeId,
      reminder_type: getReminderType(),
    });
  };

  const buttonStyle = reminderCount >= 2
    ? 'text-red-600 hover:text-red-800'
    : reminderCount >= 1
    ? 'text-amber-600 hover:text-amber-800'
    : 'text-blue-600 hover:text-blue-800';

  const Icon = reminderCount >= 2 ? AlertTriangle
    : reminderCount >= 1 ? AlertTriangle
    : Bell;

  const label = reminderCount >= 2 ? 'Напомнить строго'
    : reminderCount >= 1 ? `Напомнить повторно (${reminderCount})`
    : 'Напомнить';

  return (
    <button
      onClick={handleClick}
      disabled={createReminder.isPending}
      className={`inline-flex items-center gap-1 text-xs font-medium transition-colors ${buttonStyle}`}
    >
      {createReminder.isPending ? (
        <span className="inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : (
        <Icon className="h-3 w-3" />
      )}
      {createReminder.isPending ? 'Отправка...' : label}
    </button>
  );
}
