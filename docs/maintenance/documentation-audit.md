# Аудит документации

Дата проверки: 12 октября 2026. Метод: статическая сверка с source,
configuration, migrations, tests и CI. Runtime-команды и restore procedure
проверяются отдельно в разделе validation итогового отчёта.

## Статус документов

| Документ | Решение | Результат аудита |
|---|---|---|
| `README.md` | Обновлён | Исправлена разметка; добавлены prerequisites, verified tooling, navigation и ограничения |
| `docs/index.md` | Создан | Единая точка навигации и правила синхронизации |
| `backend/ARCHITECTURE.md` | Сохранён как исторический review | Базовые слои верны; отдельные claims о cookie, CI, Docker и runbook устарели |
| `backend/TODO.md` | Сохранён | История review полезна, но summary/count и дублированные checkbox не являются актуальным risk register |
| `frontend/TODO.md` | Сохранён | Большинство завершённых пунктов соответствует коду; это backlog/history, не architecture reference |
| `frontend/README.md` | Обновлён | Vite template boilerplate заменён проектными командами и границами |
| `docs/INFRA.md` | Обновлён | Исправлено ложное утверждение об узком CI; уточнены operational gaps |
| `docs/deploy.md` | Сохранён с правкой URL | Практический manual runbook; TLS/backup automation и проверка restore отсутствуют |
| `docs/MONEY_FLOW.md` | Сохранён | Ценная бизнес-спецификация; отдельные утверждения о полной корректности требуют regression tests |
| `docs/use-cases-contracts-payments.md` | Сохранён | Согласуется с service/task structure; не заменяет API contract |
| `docs/multi-user-roles.md` | Сохранён | Роли, membership constraints и routes подтверждены |
| `docs/BILLING.md` | Сохранён | Flow и config подтверждены; provider/live assumptions требуют внешней проверки |
| `docs/ROADMAP.md`, `docs/PRIORITIES.md` | Сохранены | Product/history; checkbox «готово» не доказывает production operation |
| `docs/PORTFOLIO.md` | Сохранён | Checklist; ожидаемые screenshots отсутствуют в проверенном inventory |
| `docs/assets/README.md` | Сохранён | Инструкция для assets |

`CONTRIBUTING.md` и `AGENTS.md` отсутствовали; созданы. `CHANGELOG.md` не
создан: в repository нет установленного release/versioning process, а
ретроспективный changelog был бы выдуманным.

## Выявленный дрейф

1. `backend/ARCHITECTURE.md` утверждал, что JWT остаётся в `localStorage`;
   фактически `core/cookies.py` и frontend axios используют HttpOnly-cookie, а
   localStorage остался только для миграции legacy sessions.
2. `docs/INFRA.md` описывал CI как lint + часть pytest; workflow уже содержит
   integration, frontend test/build и online image build.
3. Там же improvement был описан как ещё не реализованный, хотя таблица выше
   называла полный CI существующим.
4. Старый architecture review говорил, что Docker только offline и runbook
   отсутствует; оба пункта реализованы.
5. `frontend/README.md` был generic Vite template и не помогал проекту.
6. В `docs/deploy.md` указан несуществующий `/register`; реальный endpoint —
   `/v1/auth/register` (снаружи `/api/v1/auth/register`).
7. Response envelope в старых документах представлен как единый, но auth
   endpoints имеют несколько legacy formats.

## Дублирование

- `ROADMAP.md` и `PRIORITIES.md` намеренно сохраняются: первый объясняет
  стратегию, второй — исторический execution checklist.
- `backend/TODO.md` и новый technical debt register не сливаются: TODO хранит
  историю code review, register — проверенный текущий риск.
- `INFRA.md` остаётся обзором; пошаговые команды принадлежат `deploy.md`, а
  diagnostics — `operations/`.

## Не подтверждено статически

- Фактические production topology, TLS и egress rules.
- Наличие/актуальность внешних YooKassa, SMTP, Sentry accounts.
- Выполнение backup по расписанию и успешный restore.
- SLO, RPO/RTO, retention и incident ownership.
- Реальная производительность, query plans и максимальная нагрузка.
- Все product checkbox на end-to-end уровне.

## Следующий аудит

Повторить при изменении dependency lock, auth transport, deployment topology,
storage backend или API version. Автоматизировать проверку relative links и
OpenAPI diff в CI.
