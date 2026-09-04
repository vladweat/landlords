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
      setFocused(false);
      queryClient.invalidateQueries({ queryKey: ['contract-events', contractId] });
    },
    onError: (error) => showError(error, 'Ошибка добавления'),
  });

  useEffect(() => {
    if (textareaRef.current && focused) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [text, focused]);

  return (
    <div className="rounded-xl border border-gray-100 bg-gray-50/60 p-3">
      <textarea
        ref={textareaRef}
        rows={focused ? 3 : 2}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => {
          if (!text) setFocused(false);
        }}
        placeholder="Добавить заметку…"
        className="w-full resize-none rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      {focused && (
        <div className="mt-2 flex justify-end gap-2">
          <Button
            type="button"
            size="sm"
            variant="secondary"
            onClick={() => {
              setText('');
              setFocused(false);
            }}
          >
            Отмена
          </Button>
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
