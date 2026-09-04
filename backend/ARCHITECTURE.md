# Backend — архитектура и известные проблемы

Документ фиксирует текущую структуру, паттерны и результаты code review (август 2026).
Использовать как справочник при рефакторинге и онбординге — не пересканировать код заново.

**Трекер исправлений:** [TODO.md](./TODO.md)

---

## Структура репозитория

```
backend/
├── worker.py                    # re-export celery_app из app/celery_app.py
├── alembic/ + alembic.ini       # миграции БД
├── Dockerfile
├── requirements.txt
└── app/
    ├── main.py                  # FastAPI factory, exception handlers, router wiring
    ├── celery_app.py            # Celery app (broker, beat schedule)
    ├── api/
    │   ├── deps.py              # DI (repos, services, auth)
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
    │   └── rules.py             # чистая бизнес-логика (статусы, ledger, schedules)
    ├── db/
    │   ├── session.py           # SQLAlchemy engine + get_db_session
    │   ├── models/              # ORM (~14 моделей)
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

## Ресурсы домена

users/accounts, properties, tenants, contracts, rent charges, payments, reminders,
documents (PDF), contract events, feedback, dashboard (ROI, forecast, ledger).

---

## Ключевые паттерны

### Dependency injection

Централизовано в `app/api/deps.py`: `Session` → repositories → services.
Routes не должны инстанцировать repos напрямую (есть исключения — см. «Нарушения слоёв»).

### Ошибки

- Иерархия: `AppException` → `NotFoundError`, `ConflictError`, `ValidationError`, `UnauthorizedError` …
- Handlers в `app/main.py`: Pydantic → 422; `AppException` → structured JSON; catch-all → 500.
- Формат: `{"status": "success"|"error", "data": ...}` или `{"status": "error", "message": ...}`.

### Multi-tenancy

- JWT: `sub` (user_id) + `account_id` (`app/core/security.py`).
- Membership: таблица `account_memberships` (user ↔ account + role: owner/manager/accountant).
- Routes: `Depends(get_current_account_id)` — проверяет активную membership в БД; роль берётся из БД.
- Mutating routes: `Depends(require_permissions(...))` → `ForbiddenError` при отсутствии права.
- Repositories: фильтрация по `account_id` на всех read/write/delete.
- Команда: `POST/PATCH/DELETE /v1/account/members` (только owner); участник создаётся с email + паролем.

### API

- Префикс роутеров: `/v1/{resource}` (nginx: `/api/v1/...` → `/v1/...`).
- Пагинация: `PaginationParams` → `{ items, total, page, per_page, pages }`.
- Деньги: `Decimal` в domain/ORM; на frontend — строки.

### Celery

- Entry: `backend/worker.py` (broker/result = Redis).
- Tasks: `app/tasks/charge_tasks.py` — `generate_charges_for_contract`, `update_overdue_charges`.
- Beat: ежедневно в 03:00 UTC — `update_overdue_charges`.

### Новый ресурс (чеклист)

entity → interface → repo → service → schema → route → deps → тесты.

---

## Нарушения слоёв (архитектурный долг)

> **P3 (август 2026):** исправлено — feedback/events/refresh-status через сервисы; `PaginatedResult` в `domain/pagination.py`; Celery в `app/celery_app.py`; DI для `ContractEventRepository`/`AuditService`; `Session` убран из сервисов; `IContractRepository.list_all_by_account` вместо дубля `list_by_account`.

| Место | Проблема |
|-------|----------|
| ~~`api/v1/routes/feedback.py`~~ | ~~Route пишет `FeedbackModel` напрямую~~ → `FeedbackService` |
| ~~`api/v1/routes/dashboard.py` `/last-payments`~~ | ~~4 repos в route~~ → `DashboardService.get_last_payments` |
| ~~`api/v1/routes/contracts.py` `/refresh-status`~~ | ~~Route + `session.commit()`~~ → `ContractService.refresh_contract_status` |
| ~~`api/v1/routes/contracts.py` events~~ | ~~Route → repo~~ → `ContractEventService` |
| ~~`ContractService`, `PaymentService`, `ReminderService`~~ | ~~Создают repos внутри~~ → DI через `deps.py` |
| ~~`from worker import celery_app`~~ | → `app.celery_app` |
| ~~`domain/interfaces.py` → `app.api.pagination`~~ | → `domain/pagination.py` |

### Несогласованные абстракции

- ~~**`IContractRepository.list_by_account`** объявлен дважды~~ → `list_by_account` (paginated) + `list_all_by_account`.
- **`get_active_by_property`** (только `active`) vs **`get_active_for_property`** (`active` + `overdue`) — разная семантика, используются в разных сервисах.
- ~~**`IUserRepository`** не декларирует `update`/`delete`~~ → добавлены в интерфейс.

### Session в сервисах

~~`ContractService`, `PaymentService`, `ReminderService` принимают `Session` для side effects.~~
Зависимости инжектятся через DI (`event_repo`, `audit_service`); пересчёт статуса — `app/services/contract_status.py`.

### Мёртвая конфигурация

~~Redis cache (`CACHE_DEFAULT_TTL`), `APP_TIMEZONE`, `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`~~ — удалены из Settings; Celery берёт `REDIS_URL`.
~~`sentry-sdk` не подключён~~ — подключён в `main.py`.

---

## Критические баги

| # | Проблема | Файл |
|---|----------|------|
| 1 | ~~**`ValidationError` не импортирован**~~ | `api/v1/routes/auth.py`, `services/user_service.py` |
| 2 | ~~**Document download читает `doc.file_data`**~~ | `api/v1/routes/contracts.py` |
| 3 | ~~**Интеграционные тесты: неверные URL / схема property**~~ | `tests/integration/*` |
| 4 | ~~**Мёртвый метод `get_by_id_for_update`**~~ | `services/rent_charge_service.py` |

---

## Безопасность

| Проблема | Файл / место |
|----------|--------------|
| Reset-токен логируется в plaintext | `api/v1/routes/auth.py:78` |
| `/documents/` отдаётся nginx без auth (UUID-пути угадываемы) | `nginx/nginx.conf:28-33` |
| Дефолтный `SECRET_KEY` | `core/config.py:31` |
| Flower на :5555 без auth | `docker-compose.yml` |
| CORS `*` | nginx (ok для dev, опасно в prod) |
| Forgot-password не шлёт email — токен только в логах | `api/v1/routes/auth.py:69-79` |

---

## Логические баги

| Проблема | Файл |
|----------|------|
| Событие смены статуса пишется при любом update (`dto.status` может быть `None` → `"draft → None"`) | `services/contract_service.py:98-108` — guard должен быть `if dto.status and dto.status != old_status` |
| Audit log: `user_id=account_id` | `services/contract_service.py:136` |
| Domain `ValueError` не оборачивается в `ValidationError` → HTTP 500 | `domain/rules.py`, вызовы из `contract_service.py` |
| `update_payment` — закомментирована валидация суммы, нет пересчёта charge/contract | `services/payment_service.py:183-203` |
| `delete_payment` — неполный пересчёт статусов | `services/payment_service.py:205-236` |
| `create_contract_note` — нет проверки существования контракта | `api/v1/routes/contracts.py:200-215` |
| Login возвращает `NotFoundError` вместо `UnauthorizedError` — утечка «email существует» | `services/user_service.py:64,67` |

---

## Инфраструктура и тесты

### requirements.txt неполный

Отсутствуют: `python-jose`, `passlib[bcrypt]`, `reportlab`, `python-dateutil`.
Чистый `pip install -r requirements.txt` не поднимет проект.

### Docker

- `Dockerfile` копирует `.venv/site-packages` — сборка не воспроизводима из requirements.
- Celery worker без volume `storage/documents` в base compose — PDF в воркере может упасть.

### Тесты

```
tests/
├── conftest.py
├── integration/            # Alembic migrations + /v1/... URLs
├── unit/
└── tasks/test_charge_tasks.py
```

- Индексы: `account_id` на tenant-таблицах; композиты `(account_id, status)` на contracts/rent_charges; `(contract_id, status)` / `(due_date, status)` на charges.
- Нет integration-тестов: feedback, reminders, PDF/documents, Celery beat, password reset.

### Celery

~~`autoretry_for=(Exception,)`~~ — сужен до transient; locking/idempotency для bulk-tasks добавлены.
---

## Приоритеты исправления

См. чеклист с прогрессом: **[TODO.md](./TODO.md)**

---

## Мелочи (code smells)

~~Дублированный import / `utcnow` / `float()` для денег / rate-limit / комментарий-артефакт~~ — закрыто.
- CORS по-прежнему через nginx (`main.py` не дублирует).

### Bootstrap CLI

```text
python -m app.cli create-user --email … --password … --full-name …
python -m app.cli seed --email … --password …
```

Создаёт user+account (как register); `seed` дополнительно — 1 property и 1 tenant.

---

## Положительные стороны

- Слоистая архитектура в целом последовательна.
- Multi-tenancy enforced на уровне repositories.
- Repository interfaces + DI в `deps.py`.
- Domain rules отделены от БД.
- Unit-тесты на domain rules и сервисы (с моками).
- Celery для фоновых задач с beat schedule.
- Money как `Decimal` в domain/ORM.
