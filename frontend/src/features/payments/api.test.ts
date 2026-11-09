import { beforeEach, describe, expect, it, vi } from 'vitest';

const { post } = vi.hoisted(() => ({ post: vi.fn() }));

vi.mock('@/shared/api/client', () => ({
  apiClient: { post },
}));

import { paymentsApi } from './api';
import * as paymentsModule from './api';
import type { PaymentFormData } from './api';

type PaymentIdempotencyManagerFactory = (
  createId: () => string,
) => {
  keyFor: (data: PaymentFormData) => string;
  complete: () => void;
};

describe('payments API', () => {
  beforeEach(() => post.mockReset());

  it('sends the operation idempotency key with payment creation', async () => {
    const payload = {
      contract_id: 'contract-1',
      amount: '1500.00',
      date_paid: '2026-11-09',
      method: 'transfer',
    };
    const result = { payments: [{ id: 'payment-1' }], total_amount: '1500.00' };
    post.mockResolvedValue({ data: { status: 'success', data: result } });

    await expect(paymentsApi.create(payload, '16a69b65-243b-4ee5-a0f6-76a9a349a02a'))
      .resolves.toEqual(result);

    expect(post).toHaveBeenCalledWith('/payments', payload, {
      headers: { 'Idempotency-Key': '16a69b65-243b-4ee5-a0f6-76a9a349a02a' },
    });
  });

  it('reuses a key after an unknown result and starts a new key after completion', () => {
    const createManager = (
      paymentsModule as unknown as {
        createPaymentIdempotencyManager?: PaymentIdempotencyManagerFactory;
      }
    ).createPaymentIdempotencyManager;
    expect(typeof createManager).toBe('function');
    if (!createManager) return;

    const keys = ['request-1', 'request-2', 'request-3'];
    const manager = createManager(() => keys.shift() ?? 'unexpected-key');
    const payload = {
      contract_id: 'contract-1',
      amount: '1500.00',
      date_paid: '2026-11-09',
      method: 'transfer',
    };

    expect(manager.keyFor(payload)).toBe('request-1');
    expect(manager.keyFor({ ...payload })).toBe('request-1');
    expect(manager.keyFor({ ...payload, amount: '1501.00' })).toBe('request-2');
    manager.complete();
    expect(manager.keyFor(payload)).toBe('request-3');
  });
});
