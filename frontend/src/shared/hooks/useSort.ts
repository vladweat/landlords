import { useState, useMemo } from 'react';

export type SortDirection = 'asc' | 'desc' | null;

export function useSort<T>(data: T[], defaultKey: keyof T | null = null) {
  const [sortKey, setSortKey] = useState<keyof T | null>(defaultKey);
  const [sortDir, setSortDir] = useState<SortDirection>(null);

  const sorted = useMemo(() => {
    if (!sortKey || !sortDir) return data;
    return [...data].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      // Денежные суммы с API приходят строками — сравниваем как числа.
      if (typeof av === 'string' && typeof bv === 'string') {
        const an = Number(av.replace(/\s/g, '').replace(',', '.'));
        const bn = Number(bv.replace(/\s/g, '').replace(',', '.'));
        if (!Number.isNaN(an) && !Number.isNaN(bn) && av.trim() !== '' && bv.trim() !== '') {
          return sortDir === 'asc' ? an - bn : bn - an;
        }
        return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      if (typeof av === 'number' && typeof bv === 'number') {
        return sortDir === 'asc' ? av - bv : bv - av;
      }
      return 0;
    });
  }, [data, sortKey, sortDir]);

  const toggle = (key: keyof T) => {
    if (sortKey === key) setSortDir(sortDir === 'asc' ? 'desc' : sortDir === 'desc' ? null : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  };

  return { sorted, sortKey, sortDir, toggle };
}
