# Frontend Landlords

React SPA на TypeScript/Vite. Server state хранится в TanStack Query, auth
state — в Zustand. API client использует `/api/v1`, `withCredentials` и
HttpOnly-cookie; `localStorage.access_token` читается только для миграции старых
сессий.

## Запуск и проверки

```bash
# Сначала из корня: docker compose up -d
cd frontend
npm ci
npm run dev
npm test
npm run lint
npm run build
```

Vite слушает `http://localhost:3000`, `/api` проксируется в nginx на port 80.
`build` выполняет TypeScript check и production Vite build.

Структура: `app/` — router/providers, `pages/` — композиция, `features/` — API
и components, `entities/` — доменные типы, `shared/` — client/UI/lib/hooks.
Деньги в API/types остаются строками.

Общие инструкции:
[`docs/development/getting-started.md`](../docs/development/getting-started.md),
[`docs/development/testing.md`](../docs/development/testing.md). Исторический
backlog: [`TODO.md`](TODO.md).

## Справка по расширению ESLint

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])

```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])

```
