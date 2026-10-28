# План внедрения PostgreSQL RLS

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Защитить tenant-owned данные PostgreSQL RLS и отдельной непривилегированной runtime-ролью.

**Architecture:** Каждая транзакция получает `app.account_id`; политики ограничивают чтение и запись этим аккаунтом. Миграции используют owner URL, API и worker — runtime URL; публичные token flows и пакетные задачи получают узкий способ определить account ID, после чего работают под обычной RLS.

**Tech Stack:** PostgreSQL 15, SQLAlchemy 2, Alembic, FastAPI, Celery, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-10-28-platform-guardrails-design.md`

## Global Constraints

- Runtime DB role не superuser, не owner tenant-таблиц и не `BYPASSRLS`.
- Таблицы, принадлежащие аккаунту, работают по deny-by-default при отсутствии tenant context.
- Сохранить `account_id` фильтры в репозиториях как второй слой защиты.
- Не запускать тестовую fixture на обычной/production базе: она удаляет и создаёт `landlords_test`.
- Не менять финансовое поведение и не запускать миграцию на production в рамках этой работы.
- Новые env keys документировать в `.env.example` и `docs/development/configuration.md`.

## Review Focus

- Запрос без tenant context не возвращает tenant rows и не может их создать — проверить интеграционно под runtime role.
- Публичный token lookup может определить только account ID действующего токена — проверить истёкший, отозванный и чужой токен.
- Глобальная Celery задача не использует runtime role для обхода RLS — проверить изоляцию каждого account в пакетной обработке.
- Миграции, регистрации и demo seed продолжают работать после разделения owner/runtime credentials — проверить чистую test DB и существующую схему.
- Любая tenant-таблица из новых моделей включена в RLS — сравнить inventory моделей и миграций с перечнем policies.

---

### Task 1: Транзакционный tenant context

**Files:**
- Create: `backend/app/db/tenant_context.py`
- Test: `backend/tests/unit/test_tenant_context.py`
- Modify: `backend/app/db/session.py`

- [ ] Написать `test_set_tenant_context_uses_transaction_local_setting`: setter выполняет `set_config('app.account_id', account_id, true)` на переданной Session и не меняет context вне транзакции.
- [ ] Запустить `pytest -q tests/unit/test_tenant_context.py::test_set_tenant_context_uses_transaction_local_setting` и подтвердить ожидаемый провал.
- [ ] Реализовать `set_tenant_context(session: Session, account_id: UUID) -> None`; принимать UUID, не конкатенировать SQL и не коммитить Session внутри helper.
- [ ] Добавить тест на повторную установку account context после нового transaction boundary; подтвердить reset после commit/rollback реальным PostgreSQL в последующей integration task.
- [ ] Запустить unit test и сохранить только относящиеся к задаче изменения отдельным commit.

### Task 2: Разделить runtime и migration DB credentials

**Files:**
- Modify: `backend/app/core/config.py`, `backend/app/db/session.py`, `backend/alembic/env.py`, `backend/docker-entrypoint.sh`
- Modify: `docker-compose.yml`, `docker-compose.production.yml`, `docker-compose.test.yml`
- Create: `deploy/provision-runtime-db-role.sh` (или эквивалентный повторяемый bootstrap)
- Modify: `.env.example`, `docs/development/configuration.md`, `docs/deploy.md`
- Test: `backend/tests/unit/test_database_urls.py`, `backend/tests/integration/test_rls_policies.py`

- [ ] Добавить тесты, что runtime `DATABASE_URL` использует runtime credentials, Alembic URL — migration credentials, а отсутствие обязательных production credentials завершает запуск с понятной ошибкой.
- [ ] Подтвердить провал тестов до реализации.
- [ ] Добавить отдельные конфигурации runtime/migration; migration owner credentials передавать только one-shot migrate/bootstrap service, runtime URL — API и Celery.
- [ ] Добавить повторяемый role/grant bootstrap для новой и существующей PostgreSQL БД; скрипт должен безопасно обрабатывать повторный запуск и не печатать пароли.
- [ ] Встроить порядок старта Compose: bootstrap/migrate завершён успешно до старта API; API не получает owner URL.
- [ ] Проверить clean test DB и `test_runtime_role_is_not_superuser_or_table_owner`; запустить связанные unit и integration tests.
- [ ] Обновить `.env.example`, configuration и deploy runbook с предварительным шагом для существующей БД; не читать и не копировать реальные `.env`.

### Task 3: Создать RLS policies для tenant-таблиц

**Files:**
- Create: `backend/alembic/versions/<revision>_tenant_rls.py`
- Modify if needed: `backend/app/db/models/` и role bootstrap script
- Test: `backend/tests/integration/test_rls_policies.py`

- [ ] Добавить integration tests под runtime role: account A видит свои rows, account B не видит rows A, mismatched insert/update отклоняется, отсутствие context закрывает доступ.
- [ ] Запустить каждый новый тест и подтвердить провал на текущей схеме без RLS.
- [ ] Сверить полный список моделей с `account_id` и `accounts.id`; исключить только глобальные таблицы идентичности/служебные миграционные данные с обоснованием.
- [ ] Добавить `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`, `USING` и `WITH CHECK` policies с безопасной обработкой пустого `current_setting`.
- [ ] Выдать runtime role только нужные DML grants; не выдавать `ALTER`, `CREATE`, `BYPASSRLS` или ownership.
- [ ] Проверить upgrade на пустой БД и на fixture с исходными строками; downgrade должен отключать policies без удаления бизнес-данных.
- [ ] Запустить `pytest -q tests/integration/test_rls_policies.py` на изолированном Compose test stack.

### Task 4: Устанавливать контекст в HTTP и auth flows

**Files:**
- Modify: `backend/app/api/deps.py`, `backend/app/services/user_service.py`, `backend/app/services/auth_session_service.py`, связанные auth services/routes
- Test: `backend/tests/integration/test_rls_policies.py`, `backend/tests/integration/test_auth_api.py`, `backend/tests/integration/test_rbac_api.py`

- [ ] Добавить тесты, что защищённый запрос устанавливает account ID из подписанного JWT до RLS-scoped membership/session/account queries и что смена account claim без membership не даёт доступа.
- [ ] Запустить тесты и подтвердить провал из-за закрытых RLS policies.
- [ ] В `get_current_membership` установить transaction-local tenant context после проверки подписи и формата JWT, до scoped membership lookup; сохранить проверку active user/session/membership.
- [ ] Для регистрации, login, reset и invite acceptance установить правильный context до tenant-scoped read/write, не ограничивая global user lookup.
- [ ] Проверить commit/rollback boundary: следующий запрос/transaction на той же pooled connection не наследует account context.
- [ ] Запустить auth, RBAC и multi-tenancy integration suite на runtime DB role.

### Task 5: Ограничить публичные capability routes и фоновые задачи

**Files:**
- Create: `backend/app/db/repositories/tenant_context_repo.py` (если нужен узкий resolver)
- Modify: `backend/app/services/invoice_service.py`, `tenant_portal_service.py`, `invite_service.py`, `backend/app/tasks/`, `backend/app/services/outbox_relay.py`
- Modify migration from Task 3 for narrowly scoped resolver functions/policies if required
- Test: `backend/tests/integration/test_rls_public_tokens.py`, `backend/tests/tasks/`, `backend/tests/integration/test_outbox_relay.py`

- [ ] Написать failing integration tests для действующего/истёкшего/отозванного invite, invoice и portal token; тесты должны подтвердить tenant-scoped данные и запрет cross-account token substitution.
- [ ] Написать failing task tests: outbox charge-generation работает с заданным account context; пакетные overdue/reminder/billing задачи обрабатывают два аккаунта, не видя rows друг друга.
- [ ] Создать минимальные resolver entrypoints для capability token и списка account IDs пакетной работы; resolver возвращает только идентификатор, использует фиксированный `search_path`, owner-safe SQL и минимальный `EXECUTE` grant.
- [ ] Установить account context для каждой tenant-транзакции Celery; outbox relay ограничить доступом к `task_outbox`, без общего `BYPASSRLS`.
- [ ] Запустить public-token, task, outbox и financial integration tests на изолированной PostgreSQL test DB.

### Task 6: CI и документация RLS

**Files:**
- Modify: `.github/workflows/ci.yml`, `docker-compose.test.yml`, `backend/tests/integration/conftest.py`
- Modify: `docs/architecture/database.md`, `docs/api/overview.md`, `docs/architecture/background-jobs.md`, `docs/development/testing.md`, `docs/development/configuration.md`, `docs/deploy.md`

- [ ] Настроить CI fixtures: admin connection только создаёт/удаляет test database и применяет migration; API/integration client подключается runtime role.
- [ ] Добавить integration suite в CI без подключения к обычному Compose volume; проверить, что role/RLS tests действительно запускаются.
- [ ] Обновить docs про глобальные таблицы, tenant context, capability resolver, system tasks и bootstrap существующей DB.
- [ ] Запустить релевантные backend unit/task/integration suites и lint из `AGENTS.md`; зафиксировать результат и commit task.

---

## Порядок реализации

Tasks 1–3 создают механизм и доказательство на БД; Tasks 4–5 подключают все
runtime пути; Task 6 закрепляет это в CI/runbook. Не переключать публичный сервер
на runtime роль до успешного завершения всех пяти предыдущих задач.
