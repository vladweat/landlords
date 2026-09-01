# Backend — backlog исправлений

Чеклист по результатам code review. Отмечай выполненное: `- [ ]` → `- [x]`.

Справочник по архитектуре: [ARCHITECTURE.md](./ARCHITECTURE.md)

**Статус:** 47 / 66 выполнено

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
- [ ] Reproducible Docker build из `requirements.txt` (не копировать `.venv`) — `Dockerfile`, CI.
- [ ] Добавить volume `storage/documents` для API и Celery worker — `docker-compose.yml`.
- [ ] CI: lint → unit → integration → build image → security scan → smoke tests.

### Тесты, миграции и БД
- [ ] Исправить `confest.py` → `conftest.py`; адаптировать integration tests к `/v1/...` и новой схеме property.
- [ ] Использовать Alembic для integration tests (вместо `create_all`) — `alembic/versions/`.
- [ ] Проверить индексы и производительность запросов (account_id, contract_id).

### Celery и фоновые задачи
- [x] Сузить `autoretry_for` к transient‑исключениям; сделать задачи идемпотентными и account‑aware — `app/tasks/charge_tasks.py`, `app/celery_app.py`.
- [x] Добавить locking/idempotency для bulk‑tasks (update_overdue_charges).

### Наблюдаемость и безопасность
- [x] Подключить Sentry и структурированные логи; экспорт базовых метрик (Prometheus) — `app/main.py`, `app/core/config.py`.
- [x] Настроить rate‑limit для чувствительных endpoint'ов (login, forgot-password, reminders).
- [x] Health/readiness endpoints, deploy runbook и backup/restore план.

### Мелочи / техдолг
- [ ] Удалить неиспользуемые настройки и зависимости (`CACHE_DEFAULT_TTL`, `APP_TIMEZONE`, `testcontainers` в requirements).
- [ ] Добавить pre‑commit (black/isort/ruff/mypy) и enforce style в CI.
- [ ] Seed script / fixtures и скрипт создания initial admin user.

Для каждой задачи рекомендуется отдельный small PR (≈1–3ч) с описанием: цель, изменения, тест‑план и шаги отката.

---

## P0 — ломает runtime

- [x] Импортировать `ValidationError` из `app.core.exceptions` в `app/api/v1/routes/auth.py`
- [x] Импортировать `ValidationError` в `app/services/user_service.py`
- [x] Document download: читать PDF с диска по `file_path`, не `doc.file_data` — `app/api/v1/routes/contracts.py`
- [x] Удалить мёртвый метод `get_by_id_for_update` в `app/services/rent_charge_service.py`

---

## P1 — безопасность

- [ ] Убрать логирование reset-токена в plaintext — `app/api/v1/routes/auth.py:78`
- [ ] Защитить `/documents/`: proxy через API с auth или signed URLs — `nginx/nginx.conf`
- [x] Задать сильный `SECRET_KEY` через env; убрать/запретить дефолт в prod — `app/core/config.py`
- [ ] Реализовать отправку email для forgot-password (или временно отключить endpoint)
- [ ] Закрыть Flower auth или не публиковать порт в prod — `docker-compose.yml`
- [ ] Ужесточить CORS для prod (не `*`) — nginx / `main.py`

---

## P2 — бизнес-логика

- [x] Guard на событие смены статуса: только при `dto.status != old_status` — `app/services/contract_service.py`
- [x] Audit log: писать `user_id`, не `account_id` — `app/services/contract_service.py:136`
- [x] Унифицировать `get_active_by_property` / `get_active_for_property` (включать `overdue`) — `contract_repo.py`, сервисы
- [x] Оборачивать `ValueError` из `domain/rules.py` в `ValidationError` в сервисах
- [x] `update_payment`: вернуть валидацию суммы + пересчёт charge/contract — `payment_service.py`
- [x] `delete_payment`: использовать `_check_and_update_contract_status` + пересчёт charges — `payment_service.py`
- [x] `create_contract_note`: проверять существование контракта в tenant — `contracts.py`
- [x] Login: `UnauthorizedError` вместо `NotFoundError` — `user_service.py`
- [x] `update_profile`: убрать `phone` из API или добавить поле в модель — `user_schema.py`, `UserModel`

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
- [ ] Reproducible Docker build из requirements (не копировать `.venv/site-packages`)
- [x] Volume `storage/documents` для celery-worker — `docker-compose.yml`
- [x] Переименовать `tests/confest.py` → `conftest.py`
- [x] Integration tests: URL `/v1/...` вместо `/auth/`, `/properties/` …
- [x] Integration tests: актуальная схема property (`city`, `street`, `house`)
- [x] Integration tests: миграции Alembic вместо `create_all`
- [x] Celery: сузить `autoretry_for` до transient-исключений — `charge_tasks.py`
- [x] Подключить Sentry в `main.py` или убрать из deps
- [ ] Удалить неиспользуемый `testcontainers` из requirements (или начать использовать)

---

## P5 — мелочи

- [x] Убрать дублированный import — `auth.py:65-66`
- [x] Заменить `datetime.utcnow()` на timezone-aware — `entities.py`, `pdf_service.py`
- [x] Убрать `float()` для денег в dashboard/ROI (оставить Decimal/str)
- [x] Вернуть rate-limit напоминаний — `reminder_service.py`
- [x] Удалить комментарий-артеfact «В app/api/v1/routes/contracts.py добавить»
- [x] Почистить неиспользуемые настройки: `CACHE_DEFAULT_TTL`, `APP_TIMEZONE`, `CELERY_BROKER_URL`

---

## Как обновлять

1. После исправления — `- [x]` и при желании ссылка на commit/PR.
2. Обновить счётчик в шапке (можно вручную или `grep -c '\- \[x\]' TODO.md`).
3. Крупные изменения архитектуры — кратко дописать в [ARCHITECTURE.md](./ARCHITECTURE.md) (раздел «Исправлено»).

