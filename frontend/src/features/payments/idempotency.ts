import type { PaymentFormData } from './api';

export const PAYMENT_OPERATION_SAFE_RETRY_WINDOW_MS = 23 * 60 * 60 * 1000;
const STORAGE_KEY_PREFIX = 'landlords:payments:create:v1';

export interface PaymentOperationStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export interface PaymentOperation {
  key: string;
  fingerprint: string;
  createdAt: number;
}

export class PaymentOperationNeedsReconciliationError extends Error {
  constructor(
    readonly fingerprint: string,
    readonly createdAt: number,
  ) {
    super(
      'Сверьте список платежей: срок безопасного повтора этой операции истёк.',
    );
    this.name = 'PaymentOperationNeedsReconciliationError';
  }
}

export class PaymentOperationStorageError extends Error {}

interface PaymentIdempotencyManagerOptions {
  storage?: PaymentOperationStorage;
  now?: () => number;
  createId?: () => string;
  fingerprint?: (request: PaymentFormData) => Promise<string>;
}

function defaultStorage(): PaymentOperationStorage {
  try {
    if (typeof window === 'undefined')
      throw new Error('Browser storage is unavailable');
    return window.sessionStorage;
  } catch {
    throw new PaymentOperationStorageError(
      'Не удалось открыть sessionStorage для защиты платежа от повтора.',
    );
  }
}

function defaultCreateId(): string {
  if (typeof globalThis.crypto?.randomUUID !== 'function') {
    throw new PaymentOperationStorageError(
      'Браузер не поддерживает безопасную генерацию ключа операции.',
    );
  }
  return globalThis.crypto.randomUUID();
}

async function fingerprintPaymentRequest(
  request: PaymentFormData,
): Promise<string> {
  if (typeof globalThis.crypto?.subtle?.digest !== 'function') {
    throw new PaymentOperationStorageError(
      'Браузер не поддерживает безопасный fingerprint платежа.',
    );
  }
  const canonicalRequest = Object.fromEntries(
    Object.entries(request)
      .filter(([, value]) => value !== undefined)
      .sort(([left], [right]) => left.localeCompare(right)),
  );
  const digest = await globalThis.crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(JSON.stringify(canonicalRequest)),
  );
  return Array.from(new Uint8Array(digest), (value) =>
    value.toString(16).padStart(2, '0'),
  ).join('');
}

function operationStorageKey(accountId: string, fingerprint: string): string {
  return `${STORAGE_KEY_PREFIX}:${encodeURIComponent(accountId)}:${fingerprint}`;
}

function parseOperation(value: string, fingerprint: string): PaymentOperation {
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch {
    throw new PaymentOperationStorageError(
      'Состояние незавершённого платежа повреждено; запрос не отправлен.',
    );
  }

  if (
    typeof parsed !== 'object' ||
    parsed === null ||
    !('key' in parsed) ||
    typeof parsed.key !== 'string' ||
    !parsed.key ||
    !('createdAt' in parsed) ||
    typeof parsed.createdAt !== 'number' ||
    !Number.isFinite(parsed.createdAt)
  ) {
    throw new PaymentOperationStorageError(
      'Состояние незавершённого платежа повреждено; запрос не отправлен.',
    );
  }

  return { key: parsed.key, fingerprint, createdAt: parsed.createdAt };
}

const pendingPreparations = new WeakMap<
  PaymentOperationStorage,
  Map<string, Promise<PaymentOperation>>
>();

export function createPaymentIdempotencyManager(
  options: PaymentIdempotencyManagerOptions = {},
) {
  const now = options.now ?? Date.now;
  const createId = options.createId ?? defaultCreateId;
  const fingerprintRequest = options.fingerprint ?? fingerprintPaymentRequest;

  return {
    async prepare(
      accountId: string,
      request: PaymentFormData,
    ): Promise<PaymentOperation> {
      if (!accountId) {
        throw new PaymentOperationStorageError(
          'Не удалось определить аккаунт для защиты платежа от повтора.',
        );
      }
      const storage = options.storage ?? defaultStorage();
      let fingerprint: string;
      try {
        fingerprint = await fingerprintRequest(request);
      } catch {
        throw new PaymentOperationStorageError(
          'Не удалось подготовить защиту повтора платежа; запрос не отправлен.',
        );
      }
      const storageKey = operationStorageKey(accountId, fingerprint);
      let preparations = pendingPreparations.get(storage);
      if (!preparations) {
        preparations = new Map();
        pendingPreparations.set(storage, preparations);
      }
      const inProgress = preparations.get(storageKey);
      if (inProgress) return inProgress;

      const preparation = Promise.resolve().then(() => {
        let storedValue: string | null;
        try {
          storedValue = storage.getItem(storageKey);
        } catch {
          throw new PaymentOperationStorageError(
            'Не удалось прочитать состояние платежа; запрос не отправлен.',
          );
        }

        if (storedValue !== null) {
          const operation = parseOperation(storedValue, fingerprint);
          const age = now() - operation.createdAt;
          if (age < 0 || age >= PAYMENT_OPERATION_SAFE_RETRY_WINDOW_MS) {
            throw new PaymentOperationNeedsReconciliationError(
              fingerprint,
              operation.createdAt,
            );
          }
          return operation;
        }

        const operation = { key: createId(), fingerprint, createdAt: now() };
        try {
          storage.setItem(
            storageKey,
            JSON.stringify({
              key: operation.key,
              createdAt: operation.createdAt,
            }),
          );
        } catch {
          throw new PaymentOperationStorageError(
            'Не удалось сохранить защиту повтора платежа; запрос не отправлен.',
          );
        }
        return operation;
      });
      preparations.set(storageKey, preparation);
      try {
        return await preparation;
      } finally {
        if (preparations.get(storageKey) === preparation) {
          preparations.delete(storageKey);
        }
      }
    },
    complete(accountId: string, operation: PaymentOperation): void {
      const storage = options.storage ?? defaultStorage();
      const key = operationStorageKey(accountId, operation.fingerprint);
      let storedValue: string | null;
      try {
        storedValue = storage.getItem(key);
      } catch {
        throw new PaymentOperationStorageError(
          'Не удалось проверить состояние завершённого платежа.',
        );
      }
      if (storedValue === null) return;

      const storedOperation = parseOperation(
        storedValue,
        operation.fingerprint,
      );
      if (storedOperation.key !== operation.key) return;
      try {
        storage.removeItem(key);
      } catch {
        throw new PaymentOperationStorageError(
          'Не удалось очистить состояние завершённого платежа.',
        );
      }
    },
    confirmReconciled(accountId: string, fingerprint: string): void {
      const storage = options.storage ?? defaultStorage();
      const key = operationStorageKey(accountId, fingerprint);
      let storedValue: string | null;
      try {
        storedValue = storage.getItem(key);
      } catch {
        throw new PaymentOperationStorageError(
          'Не удалось прочитать незавершённую операцию.',
        );
      }
      if (storedValue === null) return;

      const operation = parseOperation(storedValue, fingerprint);
      const age = now() - operation.createdAt;
      if (age >= 0 && age < PAYMENT_OPERATION_SAFE_RETRY_WINDOW_MS) {
        throw new Error(
          'Операцию ещё можно безопасно повторить с исходным ключом.',
        );
      }
      try {
        storage.removeItem(key);
      } catch {
        throw new PaymentOperationStorageError(
          'Не удалось очистить сверенную операцию.',
        );
      }
    },
  };
}
