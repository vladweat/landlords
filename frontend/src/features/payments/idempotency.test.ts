import { beforeEach, describe, expect, it } from 'vitest';
import {
  createPaymentIdempotencyManager,
  PaymentOperationNeedsReconciliationError,
  PaymentOperationStorageError,
  type PaymentOperationStorage,
} from './idempotency';
import type { PaymentFormData } from './api';

class MemoryStorage implements PaymentOperationStorage {
  private values = new Map<string, string>();

  getItem(key: string): string | null {
    return this.values.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value);
  }

  removeItem(key: string): void {
    this.values.delete(key);
  }
}

const payload: PaymentFormData = {
  contract_id: 'contract-1',
  amount: '1500.00',
  date_paid: '2026-11-09',
  method: 'transfer',
};

describe('payment operation idempotency storage', () => {
  let now: number;
  let nextId: number;
  let storage: MemoryStorage;

  beforeEach(() => {
    now = 1_000;
    nextId = 1;
    storage = new MemoryStorage();
  });

  function createManager() {
    return createPaymentIdempotencyManager({
      storage,
      now: () => now,
      createId: () => `operation-${nextId++}`,
      fingerprint: async (request) => JSON.stringify(request),
    });
  }

  it('reuses the pending key after the component manager is recreated', async () => {
    const first = await createManager().prepare('account-1', payload);
    const afterRemount = await createManager().prepare('account-1', {
      ...payload,
    });

    expect(first.key).toBe('operation-1');
    expect(afterRemount.key).toBe(first.key);
  });

  it('coalesces concurrent preparation of the same operation', async () => {
    const operationManager = createManager();
    const [first, second] = await Promise.all([
      operationManager.prepare('account-1', payload),
      operationManager.prepare('account-1', { ...payload }),
    ]);

    expect(first.key).toBe('operation-1');
    expect(second.key).toBe(first.key);
    expect(nextId).toBe(2);
  });

  it('uses a canonical SHA-256 request fingerprint', async () => {
    const operationManager = createPaymentIdempotencyManager({
      storage,
      now: () => now,
      createId: () => 'operation-1',
    });
    const differentlyOrderedPayload = {
      method: payload.method,
      date_paid: payload.date_paid,
      amount: payload.amount,
      contract_id: payload.contract_id,
    };

    const first = await operationManager.prepare('account-1', payload);
    const second = await operationManager.prepare(
      'account-1',
      differentlyOrderedPayload,
    );

    expect(first.fingerprint).toMatch(/^[0-9a-f]{64}$/);
    expect(second.fingerprint).toBe(first.fingerprint);
    expect(second.key).toBe(first.key);
  });

  it('separates pending keys by account and payload', async () => {
    const manager = createManager();
    const first = await manager.prepare('account-1', payload);
    const changedPayload = await manager.prepare('account-1', {
      ...payload,
      amount: '1501.00',
    });
    const otherAccount = await manager.prepare('account-2', payload);

    expect(first.key).toBe('operation-1');
    expect(changedPayload.key).toBe('operation-2');
    expect(otherAccount.key).toBe('operation-3');
  });

  it('clears only the matching successful operation', async () => {
    const manager = createManager();
    const completed = await manager.prepare('account-1', payload);
    manager.complete('account-1', completed);

    const nextOperation = await manager.prepare('account-1', payload);
    expect(nextOperation.key).toBe('operation-2');
  });

  it('blocks retries after the safe window until ledger reconciliation', async () => {
    const manager = createManager();
    const stale = await manager.prepare('account-1', payload);
    now += 23 * 60 * 60 * 1000;

    await expect(manager.prepare('account-1', payload)).rejects.toBeInstanceOf(
      PaymentOperationNeedsReconciliationError,
    );

    manager.confirmReconciled('account-1', stale.fingerprint);
    const newOperation = await manager.prepare('account-1', payload);
    expect(newOperation.key).toBe('operation-2');
    manager.complete('account-1', stale);
    expect((await createManager().prepare('account-1', payload)).key).toBe(
      newOperation.key,
    );
  });

  it('fails closed when session storage cannot save an operation', async () => {
    const unavailableStorage: PaymentOperationStorage = {
      getItem: () => null,
      setItem: () => {
        throw new Error('storage disabled');
      },
      removeItem: () => undefined,
    };
    const manager = createPaymentIdempotencyManager({
      storage: unavailableStorage,
      now: () => now,
      createId: () => 'operation-1',
      fingerprint: async (request) => JSON.stringify(request),
    });

    await expect(manager.prepare('account-1', payload)).rejects.toBeInstanceOf(
      PaymentOperationStorageError,
    );
  });

  it('fails closed when it cannot read an existing operation', async () => {
    let generatedKeys = 0;
    const unreadableStorage: PaymentOperationStorage = {
      getItem: () => {
        throw new Error('storage disabled');
      },
      setItem: () => undefined,
      removeItem: () => undefined,
    };
    const manager = createPaymentIdempotencyManager({
      storage: unreadableStorage,
      now: () => now,
      createId: () => `operation-${++generatedKeys}`,
      fingerprint: async (request) => JSON.stringify(request),
    });

    await expect(manager.prepare('account-1', payload)).rejects.toBeInstanceOf(
      PaymentOperationStorageError,
    );
    expect(generatedKeys).toBe(0);
  });
});
