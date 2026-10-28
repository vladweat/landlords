import { beforeEach, describe, expect, it, vi } from 'vitest';

const { post } = vi.hoisted(() => ({ post: vi.fn() }));

vi.mock('@/shared/api/client', () => ({
  apiClient: { post },
}));

import { authApi } from './api';

describe('auth API envelope adapter', () => {
  beforeEach(() => post.mockReset());

  it('unwraps the standard auth response data for browser callers', async () => {
    const authData = {
      token: undefined,
      user: { id: 'user-1', email: 'demo@example.com', full_name: 'Demo' },
    };
    post.mockResolvedValue({ data: { status: 'success', data: authData } });

    await expect(authApi.login({ email: 'demo@example.com', password: 'secret123' }))
      .resolves.toEqual(authData);
  });

  it('unwraps successful message responses', async () => {
    const messageData = { message: 'Письмо отправлено' };
    post.mockResolvedValue({ data: { status: 'success', data: messageData } });

    await expect(authApi.forgotPassword('demo@example.com')).resolves.toEqual(messageData);
  });
});
