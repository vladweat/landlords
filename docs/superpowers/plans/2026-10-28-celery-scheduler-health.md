# План надёжности Celery scheduler и periodic tasks

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Делать отказ beat/worker/relay и ошибки periodic tasks обнаружимыми, сохраняя односерверный singleton beat и текущие бизнес-расписания.

**Architecture:** Docker healthchecks проверяют основные процессы и связь worker; Celery task instrumentation хранит агрегированные run outcomes/heartbeats в Redis без tenant labels; API `/metrics` публикует их для monitoring plan. Lock TTL остаётся длиннее hard time limit.

**Tech Stack:** Celery, Redis, Docker Compose, Prometheus client, pytest.

**Spec:** `docs/superpowers/specs/2026-10-28-platform-guardrails-design.md`

## Global Constraints

- Сохранить один `celery-beat` экземпляр и существующее расписание.
- Не логировать account IDs, emails, capability tokens или task payloads в метрики.
- Любые повторы сохраняют текущие idempotency/lock protections; бизнес-ошибки не добавлять в autoretry без отдельного обоснования.
- Тесты используют изолированные PostgreSQL/Redis из `docker-compose.test.yml` или unit mocks без обращения к production.

## Review Focus

- Проверка heartbeat не помечает beat успешным раньше времени и различает process liveness от task success.
- Worker ping проверяет ответ Celery worker, а не только соединение с Redis.
- `failed` и `skipped` остаются разными состояниями; retry policy конкретных задач не меняется случайно.
- Lock TTL превышает задачу hard time limit с запасом; docs и код совпадают.
- Redis key cardinality ограничена фиксированным перечнем именованных tasks.

---

### Task 1: Инструментировать исходы периодических задач

**Files:**
- Modify: `backend/app/celery_app.py`, `backend/app/services/ops_heartbeat.py`, `backend/app/services/ops_alert_service.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/unit/test_task_telemetry.py`, `backend/tests/unit/test_ops_alert_service.py`

- [ ] Написать failing tests для last-started, last-success, last-failure и skipped states: retry/failure не должны обновлять last-success.
- [ ] Запустить новые тесты и подтвердить провал.
- [ ] Добавить ограниченные Redis keys под `landlords:ops:tasks:<fixed_task_name>:...`; счётчики/heartbeat хранить без tenant labels и payload.
- [ ] Подключить Celery signals для начала, успеха, ошибки и skip outcome; Redis telemetry failure не должен маскировать исходную бизнес-задачу.
- [ ] Экспортировать gauges/counters из API `/metrics`, использовать фиксированный список task names и не делать пользовательские запросы к БД при scrape.
- [ ] Запустить новые unit tests и текущие tests для ops/telemetry.

### Task 2: Проверять процессы worker, beat и outbox-relay

**Files:**
- Create: `backend/app/scripts/healthcheck_celery.py` (если нужно)
- Modify: `docker-compose.yml`, `docker-compose.production.yml`
- Modify: `backend/app/outbox_relay.py`, `backend/app/services/outbox_relay.py`
- Test: `backend/tests/unit/test_celery_healthcheck.py`, `backend/tests/unit/services/test_outbox_relay.py`

- [ ] Написать тесты worker healthcheck: healthy worker отвечает на ping; Redis-only connection без worker возвращает unhealthy.
- [ ] Написать тест beat/relay heartbeat freshness: свежая отметка healthy, отсутствующая/просроченная — unhealthy.
- [ ] Запустить тесты и подтвердить провал до реализации.
- [ ] Настроить worker healthcheck через Celery remote-control ping с timeout; добавить отдельную проверку beat process и heartbeat scheduler loop.
- [ ] Добавить outbox-relay heartbeat на каждом цикле poll и healthcheck по свежести отметки.
- [ ] Не публиковать worker/beat/relay management ports наружу; проверить `docker compose config`.
- [ ] Запустить unit tests и тест на корректное завершение/повторный запуск relay.

### Task 3: Защитить lock/time-limit contract и ошибки задач

**Files:**
- Modify: `backend/app/tasks/charge_tasks.py`, `backend/app/tasks/email_tasks.py`, `backend/app/tasks/billing_tasks.py`, `backend/app/tasks/lock.py`
- Modify: `backend/tests/tasks/`, `backend/tests/unit/test_lock.py`
- Modify: `docs/architecture/database.md`, `docs/architecture/background-jobs.md`

- [ ] Добавить тесты, проверяющие для каждой периодической задачи: hard time limit меньше lock TTL; skipped state не считается успехом; autoretry policy остаётся перечисленной.
- [ ] Запустить новые tests и проверить ожидаемые текущие значения 600/900 секунд.
- [ ] Вынести значения TTL/time limit в ясные constants/settings только если это уменьшает риск расхождения; не менять существующие runtime limits без нужды.
- [ ] Убедиться, что task outcome telemetry фиксирует failure после retry и не маскирует исходное исключение.
- [ ] Согласовать устаревшее описание 600 секунд в `database.md` с кодом и `background-jobs.md`.
- [ ] Запустить backend unit/task tests и сохранить изменение отдельным commit.

### Task 4: Описать диагностику scheduler

**Files:**
- Modify: `docs/architecture/background-jobs.md`, `docs/development/testing.md`, `docs/deploy.md`

- [ ] Документировать healthcheck состояния beat/worker/relay, task outcome metrics, один экземпляр beat и safe local smoke steps.
- [ ] Явно описать, что queue acceptance не равен завершению задачи, а outbox still at-least-once.
- [ ] Проверить команды и names по Compose/CI; не добавлять команды, которые запускают бизнес-задачи на production.
- [ ] Запустить связанные docs/config checks и зафиксировать итог плана.

---

## Зависимости

Monitoring plan использует точные metric names из Task 1 и health targets из Task 2;
сначала завершить и согласовать эти интерфейсы, затем настраивать Prometheus и alerts.
