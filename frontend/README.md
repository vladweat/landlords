# Frontend Landlords

Landlords frontend is a React 19 and TypeScript single-page application built
with Vite. It uses TanStack Query for server state, Zustand for authentication
state, and Tailwind CSS for styling. The production image serves the built SPA
from nginx; `/api` requests are proxied to FastAPI.

## Local development

Use Node.js 20.19+ or 22.12+ and npm. Start the project services from the
repository root, then run Vite:

```bash
docker compose up -d
cd frontend
npm ci
npm run dev
```

Vite serves the application at `http://localhost:3000` and proxies `/api` to
nginx at `http://localhost`. The dev Compose override publishes PostgreSQL and
Redis ports for local development; do not use that override on a public host.

For the full environment setup, see
[`docs/development/getting-started.md`](../docs/development/getting-started.md).

## Checks

```bash
npm test
npm run lint
npm run build
```

`npm run build` runs TypeScript checking followed by the Vite production build.
CI runs tests and build; frontend lint is available locally but is not a CI job.
See [`docs/development/testing.md`](../docs/development/testing.md) for the
complete verification matrix.

## Source layout

- `src/app/` — router, providers and application shell;
- `src/pages/` — route-level composition;
- `src/features/` — user workflows, API adapters and feature components;
- `src/entities/` — domain types and entity UI;
- `src/shared/` — HTTP client, reusable UI and utilities.

Browser authentication uses an HttpOnly cookie. The API client reads a legacy
localStorage token only to migrate an existing session, then removes it. Money
values remain decimal strings across the API and frontend.
