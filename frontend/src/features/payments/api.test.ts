import { beforeEach, describe, expect, it, vi } from 'vitest';

const { post } = vi.hoisted(() => ({ post: vi.fn() }));

vi.mock('@/shared/api/client', () => ({
  apiClient: { post },
}));

import { paymentsApi } from './api';

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
});
