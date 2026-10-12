# Инструкции для coding agents

## Перед изменением

- Прочитать `docs/index.md` и документы затронутого subsystem.
- Проверить `git status`; не перезаписывать чужие изменения и `.env`.
- Source code, migrations, tests и runtime config важнее backlog/roadmap.
- Не смешивать documentation-only и functional changes.

## Архитектурные границы

Backend: `routes → services → repositories → models`, business rules в
`domain/`. HTTP Session коммитится в `get_db_session`; Celery управляет Session
самостоятельно. Новый resource: entity/interface → repository → service →
schema/route → DI → tests.

Multi-tenancy обязателен: все account data queries включают `account_id`.
Mutation защищается `require_permissions`; role берётся из membership в БД.
Деньги — `Decimal` backend и строки API/frontend. Депозит не входит в ledger.

Frontend: `app`, `pages`, `features`, `entities`, `shared`; TanStack Query для
server state, Zustand только для auth. Browser auth — HttpOnly-cookie.

## Проверки

```bash
cd backend && ruff check app tests --select E9,F63,F7,F82
cd backend && pytest -q tests/unit tests/tasks
cd backend && pytest -q tests/integration  # PostgreSQL/Redis
cd frontend && npm test
cd frontend && npm run build
```

Запускайте пропорционально изменению. Schema change требует Alembic migration и
integration test. Task change требует проверки retry/idempotency/lock.

## Документация

- Русский язык для docs/UI/docstrings; symbols/commands/keys — English.
- Новая config key → `.env.example` и `docs/development/configuration.md`.
- Route/auth change → `docs/api/overview.md`; model/migration →
  `docs/architecture/database.md`; task/schedule →
  `docs/architecture/background-jobs.md`.
- Не копировать большие OpenAPI schemas вручную и не публиковать secrets.
- Поддерживать relative links и помечать assumptions/gaps явно.
