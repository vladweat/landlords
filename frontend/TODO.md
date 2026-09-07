# Frontend — план доработок

Чеклист по результатам аудита `frontend/src` (сентябрь 2026).  
Стек: React 19, Vite, TanStack Query, Zustand (auth), Tailwind 4, FSD-подобная структура.

**Сборка сейчас ломается:** `npx tsc --noEmit` ≈ **44 ошибки**.  
Продукт: [ROADMAP.md](../docs/ROADMAP.md) · приоритеты: [PRIORITIES.md](../docs/PRIORITIES.md).

### Перед prod (с backend)

- [ ] Зелёный `npm run build` (см. P0 ниже)
- [ ] CI job: frontend lint + `tsc` + build — [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

Отмечай выполненное: `- [ ]` → `- [x]`.

---

## P0 — ломает runtime / деньги / auth

- [x] Починить тип `Payment` в `entities/payment.ts` (сейчас искажены поля: `date_paproperty_id`, нет `id` / `contract_id` / `date_paid`) — блокирует `PaymentsPage` и `tsc`.
- [x] 401 → полный logout: в `shared/api/client.ts` чистить Zustand (`logout()`), не только `localStorage`; `fetchUser` при ошибке тоже разлогинивать. Сейчас `ProtectedRoute` держит «залогинен» без токена.
- [x] `showError` читать `response.data.message` (формат backend `AppException`), а не только FastAPI `detail` — `shared/lib/toast.ts`.
- [x] Деньги: формы и API-payload как **string**, не `z.coerce.number()` / `number` — `PaymentModal`, `ContractModal`, `properties/schema`, типы в `entities/`.
- [x] Onboarding: `queryFn: () => api.getAll(...)`; прогресс по `data.items.length` / `total`, не `data.length` — `OnboardingWizard.tsx`.
- [x] Согласовать payment payload: `rent_charge_id` vs `charge_id` в `PaymentModal` / `features/payments/api.ts`.
- [ ] Починить `tsc` до зелёного `npm run build` (включая unused imports, zod resolver types).

## P1 — логика и UX

- [x] `billing_period` в UI либо слать на backend, либо убрать из `ContractModal` (сейчас backend всегда `monthly`).
- [x] `payment_day`: UI `.max(28)` как на backend (`le=28`), не 31.
- [x] Убрать фейковый Undo (`showUndo(..., () => {})`) на deletes **или** реализовать restore — Properties/Tenants/Contracts/Payments.
- [x] Даты `YYYY-MM-DD`: не парсить через `new Date(isoDate)` (UTC → сдвиг дня); хелпер local date — Payments, Ledger, ContractDetail, `utils.formatDate`.
- [x] Dashboard money types: `amount` / `monthly_income` как `string` (как API), не `number`.
- [x] `ReminderButton`: передать `dueDate` / `daysOverdue` с `ContractDetailPage` или упростить props.
- [x] Status update контракта: нормальный тип в API вместо `as Record<string, never>`; добавить `status` в `ContractsQuery`.
- [ ] Валидация суммы платежа ≤ остатка charge (сейчас только подсказка «макс.»). — оставлено как подсказка по задумке продукта
- [x] Settings: убрать поле `phone` или добавить на backend (сейчас silently ignored).
- [x] `useCountUp`: не `Math.floor` для денег (теряются копейки) — Dashboard.
- [x] Редирект авторизованных с `/login` / forgot / reset на `/dashboard`.
- [ ] Onboarding gate на Dashboard: не только `active_properties === 0 && active_contracts === 0`. — оставлен исходный gate

## P2 — техдолг и полиш

- [ ] Удалить мёртвое: `ForecastWidget.tsx`, `dashboardApi.getPropertiesOverview` (endpoint нет на backend), дубли `DashboardSummary` в `entities/payment.ts`.
- [ ] Убрать неиспользуемые deps: `antd`, `@ant-design/*`, `dayjs`, `magic-string` (в `src` не импортируются).
- [ ] Error Boundary вокруг protected layout.
- [ ] Mutations: `retry: 0` для create/delete платежей и договоров (избежать дублей).
- [ ] Единые toast-хелперы (`showSuccess` / `showError`); invalidate связанных query keys после payment create (dashboard, ledger).
- [ ] a11y: `aria-label` на search inputs списках.
- [ ] ContractModal: `end_date > start_date`; показ ошибок на selects property/tenant.
- [ ] Вынести CRUD-модалки из `pages/*/…Modal` в `features/*/components` (FSD).
- [ ] Frontend tests (vitest): auth store, money formatters, critical forms.
- [ ] CI: `frontend` lint + `tsc` + build (сейчас CI только backend).

---

## Рекомендуемый порядок PR

1. **Hotfix types + auth + toasts** — Payment entity, 401 logout, `message` в ошибках, зелёный `tsc`.
2. **Money as string** — схемы, API types, display helpers без float.
3. **Onboarding + contract form alignment** — wizard, `payment_day`, `billing_period`.
4. **UX honesty** — убрать fake Undo, timezone dates, ReminderButton, Settings phone.
5. **Cleanup** — dead code, unused deps, Error Boundary, CI frontend job.

Для каждой задачи — small PR с тест-планом (ручной сценарий + `tsc` / lint).
