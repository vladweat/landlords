# Backend — архитектура

Документ фиксирует структуру и паттерны backend на сентябрь 2026.

**Трекер исправлений:** [todo.md](./todo.md) · продукт: [docs/roadmap.md](../docs/roadmap.md)

> **Статус:** документ сохраняет контекст code review сентября 2026. Часть
> backlog ниже уже закрыта. Актуальное устройство системы:
> [docs/architecture/overview.md](../docs/architecture/overview.md).

---

## Что трогать не стоит

Слои `routes → services → repositories → domain/rules` уже держатся. Multi-tenancy сидит в репозиториях, деньги в домене — в `Decimal`, тесты на правила есть. Переход на async SQLAlchemy или «настоящий» DDD с агрегатами здесь ничего не даст: узкое место не в модели, а в нескольких конкретных местах ниже.

---

## Структура репозитория

```
backend/
├── worker.py                    # re-export celery_app из app/celery_app.py
├── alembic/ + alembic.ini       # миграции БД
├── Dockerfile
├── requirements.txt
├── requirements.lock
└── app/
    ├── main.py                  # FastAPI factory, exception handlers, router wiring
    ├── celery_app.py            # Celery app (broker, beat schedule)
    ├── api/
    │   ├── deps.py              # DI (repos, services, auth) — толстый; резать по доменам
    │   ├── pagination.py, responses.py, mappers.py
    │   └── v1/
    │       ├── routes/          # auth, properties, tenants, contracts, charges,
    │       │                    # payments, dashboard, reminders, feedback
    │       └── schemas/         # Pydantic request/response
    ├── core/
    │   ├── config.py, security.py, exceptions.py, logging_middleware.py
    ├── domain/
    │   ├── entities.py          # dataclass domain objects
    │   ├── interfaces.py        # Repository ABCs
    │   ├── permissions.py       # Role / Permission
    │   └── rules.py             # чистая бизнес-логика (статусы, ledger, schedules)
    ├── db/
    │   ├── session.py           # SQLAlchemy engine + get_db_session
    │   ├── models/              # ORM
    │   └── repositories/        # SQLAlchemy implementations
    ├── services/                # оркестрация бизнес-логики
    │   └── dto/
    └── tasks/
        └── charge_tasks.py      # Celery: generate charges, update overdue
```

## Поток данных

```
routes (api/v1/routes/)  →  services  →  repositories  →  models (db/models/)
                              ↓
                         domain/ (entities, interfaces, rules)
```

| Слой | Ответственность |
|------|-----------------|
| **routes** | HTTP, Pydantic-валидация, DI через `Depends`, формирование ответа. Без бизнес-логики. |
| **services** | Оркестрация, вызов `domain/rules`. DTO (`services/dto/`), не ORM. |
| **repositories** | CRUD, SQL. ABC из `domain/interfaces.py`. |
| **domain/entities** | Dataclass'ы домена. |
| **domain/rules** | Чистые функции (без БД). |
| **db/models** | SQLAlchemy ORM, `Base` + `TimestampMixin`. |

## Ключевые паттерны

### Dependency injection

Централизовано в `app/api/deps.py`: `Session` → repositories → services.
Routes не должны инстанцировать repos напрямую.

### Ошибки

- Иерархия: `AppException` → `NotFoundError`, `ConflictError`, `ValidationError`, `UnauthorizedError` …
- Handlers в `app/main.py`: Pydantic → 422; `AppException` → structured JSON; catch-all → 500.
- Формат: `{"status": "success"|"error", "data": ...}` или `{"status": "error", "message": ...}`.

### Multi-tenancy

- JWT: `sub` (user_id) + `account_id` (`app/core/security.py`).
- Membership: `account_memberships` (user ↔ account + role: owner/manager/accountant).
- Routes: `Depends(get_current_account_id)` — активная membership из БД; роль всегда из БД.
- Mutating routes: `Depends(require_permissions(...))` → `ForbiddenError`.
- Repositories: фильтрация по `account_id` на всех read/write/delete.
- Команда: `GET/PATCH/DELETE /v1/account/members` и invite `POST/GET/DELETE /v1/account/invites` (только owner); accept — `POST /v1/public/invites/{token}/accept`.

### API

- Префикс роутеров: `/v1/{resource}` (nginx: `/api/v1/...` → `/v1/...`).
- Пагинация: `PaginationParams` → `{ items, total, page, per_page, pages }`.
- Деньги: `Decimal` в domain/ORM; на API/frontend — **строки**, не `float`.

### Celery

- Entry: `backend/worker.py` (broker/result = Redis).
- Tasks: `app/tasks/charge_tasks.py` — `generate_charges_for_contract`, `update_overdue_charges`.
- Beat: ежедневно в 03:00 UTC — `update_overdue_charges`.
- HTTP-сессия коммитит сама в `get_db_session`; Celery живёт отдельно — своя сессия, свой commit/rollback.

### Новый ресурс (чеклист)

entity → interface → repo → service → schema → route → deps → тесты.

---

## Стоит поменять в коде

### Реализованные изменения

1. **Денежные значения:** `forecast_service.py`, `roi_service.py` и dashboard serialise денежные суммы строками. `float()` остаётся для процентных значений ROI и не используется для денежных сумм.
2. **N+1 в аналитике:** с 28 октября 2026 forecast, dashboard и portfolio ROI загружают связанные contracts, charges, properties, tenants, payments и expenses пакетно через account-scoped repository methods.

### 3. Три самых толстых модуля

| Файл | Строк | Что вынести |
|------|------:|-------------|
| `contract_service.py` | 509 | activate / renew / terminate в отдельные функции или маленький lifecycle-сервис |
| `pdf_service.py` | 514 | вёрстка PDF отдельно от загрузки данных |
| `api/v1/routes/contracts.py` | 354 | документы, ledger и заметки — соседние роутеры, не один |

На фронте та же история: `ContractDetailPage.tsx` (~572 строки) собирает ledger, документы, продление и расторжение. Куски уже лежат в `features/`, страница должна их только склеивать.

### 4. Дубли, которые путают

- `get_active_by_property` просто вызывает `get_active_for_property`. В интерфейсе два метода с одной семантикой. Оставить один.
- `deps.py` (~406 строк) — фабрика всего приложения; новые сервисы раздувают его дальше. Резать по доменам (auth, contracts, money), не один гигантский файл. Делать, когда в следующий раз добавляется сервис.

### 5. Сессия и ошибки в воркерах

В `charge_tasks.py` ловится голый `Exception`. Упавшая генерация начислений выглядит как «тихий» фейл. Ловить временные ошибки (сеть, дедлок), бизнес-ошибки не ретраить, писать в лог с `account_id` и `contract_id`.

(`autoretry_for` уже сужен до transient — не откатывать это.)

### 6. Фронт (исторические пункты; см. [frontend/todo.md](../frontend/todo.md))

- Переход на HttpOnly-cookie выполнен; `localStorage` читается только для
  миграции legacy sessions.
- CRUD-модалки перенесены в `features/`.
- `tsc` выполняется в `npm run build` и CI.

### 7. Типы

mypy на backend нет, в пагинации `items: list[Any]`. Имеет смысл гонять mypy хотя бы на `domain/` и `services/`, не на весь репозиторий сразу.

---

## Оставшийся порядок, если делать только код

1. Разрезать `contract_service`, PDF и роут договоров без смены поведения.
2. Слить два `get_active_*` и порезать `deps.py` при следующем изменении этих областей.
3. Расширять integration coverage для email и worker paths.

Этого достаточно, чтобы код соответствовал продукту. Новый слой абстракций и переписывание ORM ничего к этому не добавят.

---

## Безопасность

| Статус | Проблема | Файл / место |
|--------|----------|--------------|
| ~~закрыто~~ | Reset-токен в plaintext-логах | `user_service` — больше не логируется |
| ~~закрыто~~ | `/documents/` без auth | proxy через API с auth (`nginx`, routes) |
| ~~закрыто~~ | Дефолтный `SECRET_KEY` в prod | `config.py` падает, если не задан env |
| ~~закрыто~~ | Flower без auth | не публикуется / защищён в prod-профиле |
| ~~закрыто~~ | CORS `*` | ужесточён для prod |
| ~~закрыто~~ | SMTP опционален — без него письма в `storage/emails/` | `EmailService`; prod — задать `SMTP_*` |
| ~~закрыто~~ | JWT в `localStorage` на фронте (XSS) | HttpOnly-cookie; legacy migration удаляет старый token |

---

## Инфраструктура (открыто)

Полный разбор: [docs/infra.md](../docs/infra.md).

- `Dockerfile` поддерживает offline и online (`pip install -r requirements.lock`) режимы.
- CI выполняет integration + frontend test/build + online image.
- `.env.example` документирует application/DB/Redis/email/billing/ops.
- Runbook бэкапа/восстановления: [`docs/deploy.md`](../docs/deploy.md).

Volume `storage/documents` для api и celery — **готово**.

### Тесты

```
tests/
├── conftest.py
├── integration/            # Alembic migrations + /v1/... URLs
├── unit/
└── tasks/test_charge_tasks.py
```

Есть integration-тесты основных ресурсов, включая documents/invoices/portal,
RBAC и billing. Отдельных integration suites нет для feedback, reminders,
reports, notifications и contract templates; реальный Celery worker/beat в
integration tests не запускается.

---

## Исправлено ранее (P3 / code review)

> Август 2026: feedback/events/refresh-status через сервисы; `PaginatedResult` в `domain/pagination.py`; Celery в `app/celery_app.py`; DI для `ContractEventRepository`/`AuditService`; `Session` убран из сервисов; дубль `list_by_account` → `list_all_by_account`.

Критические и логические баги из первого review (ValidationError imports, document download, status events, audit `user_id`, payment recalculation, login `UnauthorizedError`) — закрыты; детали в [todo.md](./todo.md).

---

## Положительные стороны

- Слоистая архитектура в целом последовательна.
- Multi-tenancy enforced на уровне repositories.
- Repository interfaces + DI в `deps.py`.
- Domain rules отделены от БД.
- Unit-тесты на domain rules и сервисы (с моками).
- Celery для фоновых задач с beat schedule.
- Money как `Decimal` в domain/ORM (кроме forecast/ROI на выходе — см. выше).

### Bootstrap CLI

```text
python -m app.cli create-user --email … --password … --full-name …
python -m app.cli seed --email … --password …
```

Создаёт user+account (как register); `seed` дополнительно — 1 property и 1 tenant.
