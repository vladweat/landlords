# Backend — backlog исправлений

Чеклист по результатам code review. Отмечай выполненное: `- [ ]` → `- [x]`.

Справочник по архитектуре: [ARCHITECTURE.md](./ARCHITECTURE.md)

**Статус:** 13 / 38 выполнено

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
- [ ] Задать сильный `SECRET_KEY` через env; убрать/запретить дефолт в prod — `app/core/config.py`
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

- [ ] Feedback: route → service → repo (не писать ORM в route) — `feedback.py`
- [ ] Dashboard `/last-payments`: перенести в `DashboardService` — `dashboard.py`
- [ ] `/refresh-status`: перенести в service, убрать `session.commit()` из route — `contracts.py`
- [ ] Contract events: service layer вместо route → repo — `contracts.py`
- [ ] Инжектить `ContractEventRepository` / `AuditService` через DI, не создавать внутри сервисов
- [ ] Вынести Celery app в `app/celery_app.py`; убрать `from worker import celery_app`
- [ ] Убрать дубли `list_by_account` в `IContractRepository` — `domain/interfaces.py`
- [ ] Добавить `update`/`delete` в `IUserRepository`
- [ ] Перенести `PaginatedResult` из `app.api` в domain/shared (убрать domain → API)
- [ ] Убрать `Session` из сервисов или явно оформить unit-of-work

---

## P4 — инфраструктура и тесты

- [ ] Дополнить `requirements.txt`: `python-jose`, `passlib[bcrypt]`, `reportlab`, `python-dateutil`
- [ ] Reproducible Docker build из requirements (не копировать `.venv/site-packages`)
- [ ] Volume `storage/documents` для celery-worker — `docker-compose.yml`
- [ ] Переименовать `tests/confest.py` → `conftest.py`
- [ ] Integration tests: URL `/v1/...` вместо `/auth/`, `/properties/` …
- [ ] Integration tests: актуальная схема property (`city`, `street`, `house`)
- [ ] Integration tests: миграции Alembic вместо `create_all`
- [ ] Celery: сузить `autoretry_for` до transient-исключений — `charge_tasks.py`
- [ ] Подключить Sentry в `main.py` или убрать из deps
- [ ] Удалить неиспользуемый `testcontainers` из requirements (или начать использовать)

---

## P5 — мелочи

- [ ] Убрать дублированный import — `auth.py:65-66`
- [ ] Заменить `datetime.utcnow()` на timezone-aware — `entities.py`, `pdf_service.py`
- [ ] Убрать `float()` для денег в dashboard/ROI (оставить Decimal/str)
- [ ] Вернуть rate-limit напоминаний — `reminder_service.py`
- [ ] Удалить комментарий-артеfact «В app/api/v1/routes/contracts.py добавить»
- [ ] Почистить неиспользуемые настройки: `CACHE_DEFAULT_TTL`, `APP_TIMEZONE`, `CELERY_BROKER_URL`

---

## Как обновлять

1. После исправления — `- [x]` и при желании ссылка на commit/PR.
2. Обновить счётчик в шапке (можно вручную или `grep -c '\- \[x\]' TODO.md`).
3. Крупные изменения архитектуры — кратко дописать в [ARCHITECTURE.md](./ARCHITECTURE.md) (раздел «Исправлено»).
