import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const landingPage = readFileSync(
  resolve('public/landing.html'),
  'utf8',
);

describe('public demo access', () => {
  it('does not publish the local synthetic demo credentials', () => {
    expect(landingPage).not.toContain('demo@example.com');
    expect(landingPage).not.toContain('ChangeMeDemo1!');
    expect(landingPage).not.toContain('публичный демонстрационный аккаунт');
    expect(landingPage).toContain(
      'Публичный демонстрационный аккаунт недоступен',
    );
    expect(landingPage).toContain(
      'https://github.com/vladweat/landlords/blob/main/docs/deploy.md',
    );
  });
});
