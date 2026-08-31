import { useState, useMemo } from 'react';

export type SortDirection = 'asc' | 'desc' | null;

export function useSort<T>(data: T[], defaultKey: keyof T | null = null) {
  const [sortKey, setSortKey] = useState<keyof T | null>(defaultKey);
  const [sortDir, setSortDir] = useState<SortDirection>(null);

  const sorted = useMemo(() => {
    if (!sortKey || !sortDir) return data;
    return [...data].sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey];
      if (typeof av === 'string' && typeof bv === 'string') return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      if (typeof av === 'number' && typeof bv === 'number') return sortDir === 'asc' ? av - bv : bv - av;
      return 0;
    });
  }, [data, sortKey, sortDir]);

  const toggle = (key: keyof T) => {
    if (sortKey === key) setSortDir(sortDir === 'asc' ? 'desc' : sortDir === 'desc' ? null : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  };

  return { sorted, sortKey, sortDir, toggle };
}
