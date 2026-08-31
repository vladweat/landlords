export function exportCSV<T extends Record<string, unknown>>(data: T[], filename: string, headers: string[], keys: (keyof T)[]) {
  const csv = [headers.join(','), ...data.map((row) => keys.map((k) => `"${row[k] ?? ''}"`).join(','))].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${filename}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
