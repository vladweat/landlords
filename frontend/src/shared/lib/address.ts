export function shortAddress(full: string): string {
  const parts = full.split(', ');
  if (parts.length >= 3) return `${parts[1]}, ${parts[2]}`;
  if (parts.length === 2) return parts[1];
  return full;
}
