# Backend — архитектура и известные проблемы

Документ фиксирует текущую структуру, паттерны и результаты code review (август 2026).
Использовать как справочник при рефакторинге и онбординге — не пересканировать код заново.

**Трекер исправлений:** [TODO.md](./TODO.md)

---

## Структура репозитория

```
backend/
├── worker.py                    # Celery app (broker, beat schedule)
├── alembic/ + alembic.ini       # миграции БД
├── Dockerfile
├── requirements.txt
└── app/
    ├── main.py                  # FastAPI factory, exception handlers, router wiring
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
- Routes: `Depends(get_current_account_id)`.
- Repositories: фильтрация по `account_id` на всех read/write/delete.

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

| Место | Проблема |
|-------|----------|
| `api/v1/routes/feedback.py` | Route пишет `FeedbackModel` напрямую через `Session`, без service/repo |
| `api/v1/routes/dashboard.py` `/last-payments` | 4 repos в route, не в `DashboardService` |
| `api/v1/routes/contracts.py` `/refresh-status` | Route собирает repos, вызывает `_check_and_update_contract_status`, делает `session.commit()` |
| `api/v1/routes/contracts.py` events | Route → `ContractEventRepository` напрямую |
| `ContractService`, `PaymentService`, `ReminderService` | Создают `ContractEventRepository` / `AuditService` внутри методов |
| `ContractService`, routes | `from worker import celery_app` — coupling на путь модуля |
| `domain/interfaces.py` | Импортирует `PaginatedResult` из `app.api.pagination` (domain → API) |

### Несогласованные абстракции

- **`IContractRepository.list_by_account`** объявлен дважды с разными сигнатурами (строки ~133 и ~166) — второй перекрывает первый.
- **`get_active_by_property`** (только `active`) vs **`get_active_for_property`** (`active` + `overdue`) — разная семантика, используются в разных сервисах.
- **`IUserRepository`** не декларирует `update`/`delete`, хотя `UserRepository` и `UserService` их используют.

### Session в сервисах

`ContractService`, `PaymentService`, `ReminderService` принимают `Session` для side effects (events, audit).
Размывает границы транзакций, провоцирует создание repos внутри методов.

### Мёртвая конфигурация

- Redis cache (`CACHE_DEFAULT_TTL`) — не используется.
- `APP_TIMEZONE` — не используется.
- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` — пустые; `worker.py` берёт `REDIS_URL`.
- `sentry-sdk` в requirements — не подключён в `main.py`.

---

## Критические баги

| # | Проблема | Файл |
|---|----------|------|
| 1 | **`ValidationError` не импортирован** — `NameError` при reset/change password, delete account | `api/v1/routes/auth.py:90`, `services/user_service.py:111,130,132,140` |
| 2 | **Document download читает `doc.file_data`**, но поле удалено из БД; файлы на диске (`file_path`) | `api/v1/routes/contracts.py:180-184` |
| 3 | **Интеграционные тесты: неверные URL** (`/auth/` вместо `/v1/auth/`) и устаревшая схема property (`address` вместо `city`/`street`/`house`) | `tests/integration/*` |
| 4 | **Мёртвый метод `get_by_id_for_update`** в `RentChargeService` — ссылается на `self.session`, `RentChargeModel` | `services/rent_charge_service.py:137-145` |

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
| `UpdateProfileRequest.phone` принимается, но не сохраняется | `services/user_service.py:115-123` |

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
├── confest.py              # ОПЕЧАТКА — должно быть conftest.py; pytest не загружает
├── integration/            # conftest.py + 8 модулей (URL и схемы устарели)
├── unit/                   # domain + 7 service modules (mock repos — ok)
└── tasks/test_charge_tasks.py
```

- Integration: `Base.metadata.create_all` вместо Alembic — drift схемы.
- `testcontainers` в requirements — не используется.
- Нет integration-тестов: feedback, reminders, PDF/documents, Celery beat, password reset.

### Celery

- `autoretry_for=(Exception,)` — ретраит программные ошибки, не только transient.
- `update_overdue_charges` — bulk update по всем аккаунтам без `account_id` (ok для cron, но без locking/idempotency).

---

## Приоритеты исправления

См. чеклист с прогрессом: **[TODO.md](./TODO.md)**

---

## Мелочи (code smells)

- Дублированный import в `auth.py:65-66`
- `datetime.utcnow()` — deprecated
- `float()` для денег в dashboard/ROI
- Rate-limit напоминаний закомментирован (`reminder_service.py:75-77`)
- Комментарий-артеfact `# В app/api/v1/routes/contracts.py добавить:` в production-коде
- CORS закомментирован в `main.py` (nginx обрабатывает)

---

## Положительные стороны

- Слоистая архитектура в целом последовательна.
- Multi-tenancy enforced на уровне repositories.
- Repository interfaces + DI в `deps.py`.
- Domain rules отделены от БД.
- Unit-тесты на domain rules и сервисы (с моками).
- Celery для фоновых задач с beat schedule.
- Money как `Decimal` в domain/ORM.
