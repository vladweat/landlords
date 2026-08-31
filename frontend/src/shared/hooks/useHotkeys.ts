import { useEffect } from 'react';

type HotkeyMap = Record<string, () => void>;

export function useHotkeys(keys: HotkeyMap) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement) return;
      const key = e.key.toLowerCase();
      if (keys[key]) {
        e.preventDefault();
        keys[key]();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [keys]);
}
