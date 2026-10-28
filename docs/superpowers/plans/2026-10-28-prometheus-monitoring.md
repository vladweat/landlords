# План мониторинга односерверного Landlords

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Добавить внутренние dashboards и alerts для Landlords/VPS, не открывая мониторинг в публичный интернет.

**Architecture:** Prometheus scrape API/task metrics и Postgres/Redis/host exporters внутри Compose network; Grafana и Alertmanager работают как внутренние services. Grafana доступна только на localhost для SSH tunnel; дежурные email/Sentry alerts используют явную конфигурацию.

**Tech Stack:** Prometheus, Grafana, Alertmanager, PostgreSQL exporter, Redis exporter, node exporter, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-10-28-platform-guardrails-design.md`

## Global Constraints

- Сервисы мониторинга не добавлять в public Caddy routes и не публиковать на `0.0.0.0`.
- У images задавать проверенные конкретные version tags; не использовать `latest`.
- Retention и persistent volumes должны быть явными и ограниченными для VPS.
- Exporter credentials передавать secrets/env files; не помещать их в dashboards, labels или Git.
- Task metrics использовать bounded-cardinality names из `celery-scheduler-health.md`; account ID, email и token labels запрещены.

## Review Focus

- Grafana bind остаётся на `127.0.0.1`; Prometheus, Alertmanager и exporters доступны только внутри Compose network.
- Prometheus config/rules и Grafana provisioning валидны для закреплённых image versions.
- DB/Redis exporter credentials имеют только read-only/monitoring права.
- Alerts переживают краткий Compose restart без лишнего шума и срабатывают на настоящую потерю target.
- Мониторинг не заполняет диск без retention cap и не использует рабочие объёмы БД.

---

### Task 1: Compose services и секреты мониторинга

**Files:**
- Create: `monitoring/prometheus.yml`, `monitoring/alertmanager.yml`
- Create: `monitoring/rules/landlords.yml`
- Modify: `docker-compose.yml`, `docker-compose.production.yml`, `.env.example`
- Modify: `docs/development/configuration.md`, `docs/deploy.md`

- [ ] Добавить Compose config tests: Grafana bind localhost, Prometheus/Alertmanager/exporter без host ports, volume/retention задан, мониторинг не поднимает DB/Redis без текущих сервисов.
- [ ] Подтвердить провал проверок до конфигурации.
- [ ] Добавить version-pinned Prometheus, Grafana, Alertmanager и exporters; выбрать конкретные стабильные версии по официальным upstream images/docs перед записью.
- [ ] Сконфигурировать targets для API `/metrics`, node exporter, PostgreSQL exporter, Redis exporter и task metrics из scheduler plan.
- [ ] Настроить Grafana localhost-only access, persistent dashboard volume и явный datasource provisioning.
- [ ] Настроить Alertmanager receiver на существующий operational email через отдельные runtime secrets; Sentry остаётся дополнительным каналом приложения.
- [ ] Проверить env examples, volumes, secrets и `docker compose -f docker-compose.yml -f docker-compose.production.yml config`.

### Task 2: Dashboards и alert rules

**Files:**
- Create: `monitoring/grafana/dashboards/landlords-overview.json`
- Create: `monitoring/grafana/provisioning/datasources/prometheus.yml`
- Create: `monitoring/grafana/provisioning/dashboards/dashboards.yml`
- Modify: `monitoring/rules/landlords.yml`
- Test: `monitoring/tests/` (config/rule validation script)

- [ ] Добавить validation cases для API/DB/Redis target down, stale beat/worker, task failures, terminal outbox errors и disk threshold; исключить tenant labels.
- [ ] Проверить, что новые правила падают на отсутствующих/malformed metric names.
- [ ] Добавить минимальный обзорный dashboard: availability, HTTP errors/latency, DB/Redis health, disk free, last scheduled task success, skipped/failure counts, outbox backlog.
- [ ] Добавить Alertmanager rules с задержками `for` для transient restart noise и отдельным severity для data/queue failure.
- [ ] Проверить Prometheus config/rules через `promtool check config` и `promtool check rules`; проверить JSON dashboard parse.

### Task 3: Exporter permissions и end-to-end smoke

**Files:**
- Create or modify: `deploy/monitoring/` credential/bootstrap scripts if required
- Modify: `.github/workflows/ci.yml`, `docs/deploy.md`, `docs/development/testing.md`
- Test: `monitoring/tests/test_compose_monitoring.py` (or shell smoke script)

- [ ] Добавить тест, что exporter users не имеют write/superuser privileges и monitoring services не публикуются наружу.
- [ ] Запустить test до role/config изменений и подтвердить ожидаемый провал.
- [ ] Создать read-only PostgreSQL metrics role и ограниченного Redis exporter user; передавать пароли через secret files.
- [ ] Запустить monitoring Compose на изолированном test stack; проверить Prometheus targets `UP`, Grafana datasource и тестовый alert delivery без рабочей почты.
- [ ] Проверить остановку/восстановление одного exporter: alert появляется после `for` и разрешается после восстановления.
- [ ] Добавить CI validation для Compose, Prometheus config/rules и Grafana JSON без подключения к production.
- [ ] Документировать SSH-tunnel доступ, retention, alerts setup/verify и очистку только тестовых volumes; запустить релевантные checks и зафиксировать commit.

---

## Зависимость

Начать после согласования metric names и health checks из
`2026-10-28-celery-scheduler-health.md`. Образы мониторинга и exporter grants
сверить с официальными upstream материалами перед установкой версий.
