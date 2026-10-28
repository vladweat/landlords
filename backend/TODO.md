# Backend — исторический checklist code review

Checkboxes ниже фиксируют состояние на момент прежних ревью и не являются
актуальным backlog: часть пунктов закрыта последующими изменениями, часть
нуждается в новой проверке. Текущие подтверждённые риски ведутся только в
[`docs/maintenance/technical-debt.md`](../docs/maintenance/technical-debt.md).
Проверенную архитектуру см. в [`docs/architecture/overview.md`](../docs/architecture/overview.md).

Чеклист по результатам code review. Отмечай выполненное: `- [ ]` → `- [x]`.

Справочник по архитектуре: [ARCHITECTURE.md](./ARCHITECTURE.md)

**Статус:** исторический подсчёт на дату прежнего code review. Не использовать
как текущую оценку; актуальный реестр: [technical debt](../docs/maintenance/technical-debt.md).

---

## Перед запуском — приоритетный backlog

Ниже приоритетные задачи, которые рекомендуется закрыть перед production‑запуском.

### Срочно — критично (P0 / P1)
- [X] Убрать логирование reset‑токена и реализовать реальный forgot‑password flow — `app/api/v1/routes/auth.py`, `app/services/user_service.py`, `app/core/config.py`.
- [x] Защитить доступ к документам (PDF): proxy через API с auth или signed URLs — `nginx/nginx.conf`, `app/api/v1/routes/contracts.py`.
- [x] Запретить дефолтный `SECRET_KEY`; требовать значение через env в prod — `app/core/config.py`, `.env.example`.
- [X] Закрыть или защитить Flower в prod — `docker-compose.yml`.
- [X] Ужесточить CORS и security headers в prod — `nginx/nginx.conf`, `app/main.py`.

### Инфраструктура и CI
> Детали и порядок: [docs/INFRA.md](../docs/INFRA.md). Offline-`.venv` **не удалять** — нужен для офлайн-сборки.

- [x] Docker: online-режим (`pip install -r requirements.txt`) рядом с offline (`COPY .venv`) — build-arg / target — `Dockerfile`, CI.
- [x] Добавить volume `storage/documents` для API и Celery worker — `docker-compose.yml`.
- [x] Старт контейнера: `alembic upgrade head` → uvicorn; healthcheck на `/ready`.
- [x] CI: lint → unit → integration (Postgres/Redis) → frontend `tsc`/build → online image. Деплой — отдельный job.
- [x] Заполнить root `.env.example` (SECRET_KEY, Postgres, SMTP).
- [x] Один вход: nginx → API + Vite-статика; убрать конфликт порта 80 с `frontend`.
- [x] Prod: Postgres/Redis без `ports` на хост; TLS; CORS не localhost.
- [x] Бэкап/restore: Postgres + `storage/documents` → записать в [docs/deploy.md](../docs/deploy.md).

### Код (без смены поведения) — порядок в ARCHITECTURE.md
- [x] Убрать `float()` для денежных значений из `forecast_service.py` / `roi_service.py` — суммы в JSON отдаются строками; проценты ROI остаются числами.
- [x] N+1: batch-запросы charges/properties/contracts/payments/expenses для forecast, dashboard и ROI; account-scoped методы в repositories.
- [ ] Разрезать `contract_service` (lifecycle), `pdf_service` (layout vs data), `routes/contracts.py` (документы/ledger/заметки).
- [ ] Слить `get_active_by_property` → один метод с `get_active_for_property`.
- [ ] Резать `deps.py` по доменам при следующем новом сервисе.
- [ ] Celery: не ловить голый `Exception`; лог с `account_id` / `contract_id` — `charge_tasks.py`.
- [ ] mypy хотя бы на `domain/` и `services/`.

### Тесты, миграции и БД
- [x] Исправить `confest.py` → `conftest.py`; адаптировать integration tests к `/v1/...` и новой схеме property.
- [x] Использовать Alembic для integration tests (вместо `create_all`) — `alembic/versions/`.
- [x] Проверить индексы и производительность запросов (account_id, contract_id).

### Celery и фоновые задачи
- [x] Сузить `autoretry_for` к transient‑исключениям; сделать задачи идемпотентными и account‑aware — `app/tasks/charge_tasks.py`, `app/celery_app.py`.
- [x] Добавить locking/idempotency для bulk‑tasks (update_overdue_charges).

### Наблюдаемость и безопасность
- [x] Подключить Sentry и структурированные логи; экспорт базовых метрик (Prometheus) — `app/main.py`, `app/core/config.py`.
- [x] Настроить rate‑limit для чувствительных endpoint'ов (login, forgot-password, reminders).
- [x] Health/readiness endpoints (`/health`, `/ready`) в API.
- [x] Deploy runbook и backup/restore — процедуры в репозитории нет → [docs/deploy.md](../docs/deploy.md), [INFRA.md](../docs/INFRA.md).

### Мелочи / техдолг
- [x] Удалить неиспользуемые настройки и зависимости (`CACHE_DEFAULT_TTL`, `APP_TIMEZONE`, `testcontainers` в requirements).
- [x] Добавить pre‑commit (black/ruff; import-sort через ruff) и enforce style в CI.
- [x] Seed script / fixtures и скрипт создания initial admin user.

Для каждой задачи рекомендуется отдельный small PR (≈1–3ч) с описанием: цель, изменения, тест‑план и шаги отката.

---

## P0 — ломает runtime

- [x] Импортировать `ValidationError` из `app.core.exceptions` в `app/api/v1/routes/auth.py`
- [x] Импортировать `ValidationError` в `app/services/user_service.py`
- [x] Document download: читать PDF с диска по `file_path`, не `doc.file_data` — `app/api/v1/routes/contracts.py`
- [x] Удалить мёртвый метод `get_by_id_for_update` в `app/services/rent_charge_service.py`

---

## P1 — безопасность

> Дублирует «Перед запуском»; актуальный статус — там. Ниже для истории code review.

- [x] Убрать логирование reset-токена в plaintext — `user_service.request_password_reset`
- [x] Защитить `/documents/`: proxy через API с auth — `nginx/nginx.conf`, routes
- [x] Задать сильный `SECRET_KEY` через env; убрать/запретить дефолт в prod — `app/core/config.py`
- [x] Forgot-password: SMTP или dev-файл в `storage/password_resets` — `user_service.py`
- [x] Закрыть Flower auth или не публиковать порт в prod — `docker-compose.yml`
- [x] Ужесточить CORS для prod (не `*`) — nginx / `main.py`

---

## P2 — бизнес-логика

- [x] Guard на событие смены статуса: только при `dto.status != old_status` — `app/services/contract_service.py`
- [x] Audit log: писать `user_id`, не `account_id` — `app/services/contract_service.py:136`
- [x] Семантика active+overdue в `get_active_for_property` — `contract_repo.py`, сервисы
- [ ] Слить дубль `get_active_by_property` → один метод (сейчас просто делегирует)
- [x] Оборачивать `ValueError` из `domain/rules.py` в `ValidationError` в сервисах
- [x] `update_payment`: вернуть валидацию суммы + пересчёт charge/contract — `payment_service.py`
- [x] `delete_payment`: использовать `_check_and_update_contract_status` + пересчёт charges — `payment_service.py`
- [x] `create_contract_note`: проверять существование контракта в tenant — `contracts.py`
- [x] Login: `UnauthorizedError` вместо `NotFoundError` — `user_service.py`
- [x] `update_profile`: добавить `phone` в модель и API — `user_schema.py`, `UserModel`

---

## P3 — архитектура

- [x] Feedback: route → service → repo (не писать ORM в route) — `feedback.py`
- [x] Dashboard `/last-payments`: перенести в `DashboardService` — `dashboard.py`
- [x] `/refresh-status`: перенести в service, убрать `session.commit()` из route — `contracts.py`
- [x] Contract events: service layer вместо route → repo — `contracts.py`
- [x] Инжектить `ContractEventRepository` / `AuditService` через DI, не создавать внутри сервисов
- [x] Вынести Celery app в `app/celery_app.py`; убрать `from worker import celery_app`
- [x] Убрать дубли `list_by_account` в `IContractRepository` — `domain/interfaces.py`
- [x] Добавить `update`/`delete` в `IUserRepository`
- [x] Перенести `PaginatedResult` из `app.api` в domain/shared (убрать domain → API)
- [x] Убрать `Session` из сервисов или явно оформить unit-of-work

---

## P4 — инфраструктура и тесты

- [x] Дополнить `requirements.txt`: `python-jose`, `passlib[bcrypt]`, `reportlab`, `python-dateutil`
- [ ] Docker online-режим из requirements (+ сохранить offline `.venv`) — см. INFRA.md
- [x] Volume `storage/documents` для celery-worker — `docker-compose.yml`
- [x] Переименовать `tests/confest.py` → `conftest.py`
- [x] Integration tests: URL `/v1/...` вместо `/auth/`, `/properties/` …
- [x] Integration tests: актуальная схема property (`city`, `street`, `house`)
- [x] Integration tests: миграции Alembic вместо `create_all`
- [x] Celery: сузить `autoretry_for` до transient-исключений — `charge_tasks.py`
- [x] Подключить Sentry в `main.py` или убрать из deps
- [x] Удалить неиспользуемый `testcontainers` из requirements (или начать использовать)

---

## P5 — мелочи

- [x] Убрать дублированный import — `auth.py:65-66`
- [x] Заменить `datetime.utcnow()` на timezone-aware — `entities.py`, `pdf_service.py`
- [x] Убрать `float()` для денег в forecast/ROI (суммы отдавать строками; проценты остаются числами) — `forecast_service.py`, `roi_service.py`
- [x] Вернуть rate-limit напоминаний — `reminder_service.py`
- [x] Удалить комментарий-артеfact «В app/api/v1/routes/contracts.py добавить»
- [x] Почистить неиспользуемые настройки: `CACHE_DEFAULT_TTL`, `APP_TIMEZONE`, `CELERY_BROKER_URL`

---

## Как обновлять

1. После исправления — `- [x]` и при желании ссылка на commit/PR.
2. Обновить счётчик в шапке (можно вручную или `grep -c '\- \[x\]' TODO.md`).
3. Крупные изменения архитектуры — кратко дописать в [ARCHITECTURE.md](./ARCHITECTURE.md) (раздел «Исправлено»).

