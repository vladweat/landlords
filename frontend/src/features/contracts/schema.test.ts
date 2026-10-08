import { describe, expect, it } from 'vitest';
import { contractSchema } from './schema';

const valid = {
  property_id: 'p1',
  tenant_id: 't1',
  rent_amount: '10000',
  currency: 'RUB',
  start_date: '2026-01-01',
  end_date: '2026-12-31',
  payment_day: 5,
  billing_period: 'monthly' as const,
  deposit_amount: '',
  auto_generate_charges: false,
};

describe('contractSchema', () => {
  it('принимает договор с датой окончания позже начала', () => {
    expect(contractSchema.safeParse(valid).success).toBe(true);
  });

  it('отклоняет end_date раньше или равную start_date', () => {
    const same = contractSchema.safeParse({ ...valid, end_date: '2026-01-01' });
    const earlier = contractSchema.safeParse({ ...valid, end_date: '2025-12-01' });
    expect(same.success).toBe(false);
    expect(earlier.success).toBe(false);
    if (!same.success) {
      expect(same.error.issues.some((issue) => issue.path.join('.') === 'end_date')).toBe(true);
    }
  });

  it('показывает ошибки выбора объекта и арендатора', () => {
    const result = contractSchema.safeParse({ ...valid, property_id: '', tenant_id: '' });
    expect(result.success).toBe(false);
    if (!result.success) {
      const messages = result.error.issues.map((issue) => issue.message);
      expect(messages).toContain('Выберите объект');
      expect(messages).toContain('Выберите арендатора');
    }
  });
});
