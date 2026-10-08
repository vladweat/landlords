import { describe, expect, it } from 'vitest';
import { formatCurrency, formatDate, parseLocalDate } from './utils';

describe('parseLocalDate', () => {
  it('читает YYYY-MM-DD как локальную дату', () => {
    const date = parseLocalDate('2026-03-08');
    expect(date.getFullYear()).toBe(2026);
    expect(date.getMonth()).toBe(2);
    expect(date.getDate()).toBe(8);
  });
});

describe('formatDate', () => {
  it('форматирует календарную дату без сдвига дня', () => {
    expect(formatDate('2026-03-08')).toBe('08.03.2026');
  });
});

describe('formatCurrency', () => {
  it('форматирует сумму в рублях', () => {
    const formatted = formatCurrency(1500.5, 'RUB');
    expect(formatted.replace(/\s/g, ' ')).toContain('1');
    expect(formatted).toMatch(/₽|RUB/);
  });
});
