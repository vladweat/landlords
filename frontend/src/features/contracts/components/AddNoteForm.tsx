import { useState, useRef, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { contractsApi } from '@/features/contracts/api';
import { showError } from '@/shared/lib/toast';
import { Button } from '@/shared/ui/Button';

interface AddNoteFormProps {
  contractId: string;
}

export function AddNoteForm({ contractId }: AddNoteFormProps) {
  const queryClient = useQueryClient();
  const [text, setText] = useState('');
  const [focused, setFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const mutation = useMutation({
    mutationFn: () => contractsApi.createNote(contractId, text.slice(0, 50), text),
    onSuccess: () => {
      setText('');
      queryClient.invalidateQueries({ queryKey: ['contract-events', contractId] });
    },
    onError: (error) => showError(error, 'Ошибка добавления'),
  });

  useEffect(() => {
    if (textareaRef.current && focused) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [text, focused]);

  const rows = focused ? 4 : 2;

  return (
    <div className="mb-4">
      <textarea
        ref={textareaRef}
        rows={rows}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => { if (!text) setFocused(false); }}
        placeholder="Добавить заметку..."
        className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      />
      {focused && (
        <div className="flex justify-end mt-2">
          <Button
            size="sm"
            onClick={() => mutation.mutate()}
            disabled={!text.trim() || mutation.isPending}
            isLoading={mutation.isPending}
          >
            Добавить
          </Button>
        </div>
      )}
    </div>
  );
}
