# Landlords — инфраструктура и деплой

Локальный и VPS-стек на Docker Compose. Операционный runbook — [deploy.md](./deploy.md). Портфолио — [PORTFOLIO.md](./PORTFOLIO.md).

Продуктовый порядок: [ROADMAP.md](./ROADMAP.md) · чеклист: [PRIORITIES.md](./PRIORITIES.md).

---

## Что уже есть

В `docker-compose.yml`: API, Celery worker, beat и outbox-relay, Postgres 15,
Redis 7, nginx (SPA + `/api`). Flower — профиль `development`. У API:
`/health`, `/ready` (БД + Redis), `/metrics`. Sentry и Prometheus client
подключены. Документы — volume `storage/documents`. Dev override монтирует
исходники и включает `--reload`.

**Сборка API** — два режима через `INSTALL_MODE`:

| Режим | Когда | Как |
|-------|-------|-----|
| `offline` (default) | нет PyPI на машине сборки | копирует `.venv` (Python 3.12) |
| `online` | CI / чистая машина | `pip install -r requirements.lock` |

Entrypoint API при `RUN_MIGRATIONS=1` гоняет `alembic upgrade head`. Healthcheck смотрит на `/ready`.

**Публичный вход:** base nginx отдаёт собранный фронт и проксирует API по HTTP.
`docker-compose.production.yml` добавляет Caddy для HTTPS и привязывает nginx к
`127.0.0.1:8080`; Postgres и Redis не публикуют host ports. `.env.example` —
локальный шаблон, а не production-конфигурация. В runtime встроенный
`SECRET_KEY` placeholder `change-me-in-production-change-me` запрещён при
`APP_ENV=production`. Шаблон использует другое значение — `change_me`, которое
текущая startup-проверка принимает; его обязательно замени уникальным случайным
ключом. Это несоответствие зарегистрировано в
[техническом долге](maintenance/technical-debt.md).

**Публичная регистрация** управляется `ALLOW_PUBLIC_REGISTRATION` (для портфолио/прода — `false`). Bootstrap через CLI: `python -m app.cli seed-demo`.

**Данные:** процедура бэкапа/restore — в [deploy.md](./deploy.md). Ops-алерты (beat stale, диск документов) и публичный `/status` — см. тот же runbook.

---

## Что ещё улучшить

**CI** (`.github/workflows/ci.yml`) выполняет critical Ruff checks, unit/tasks,
integration с PostgreSQL/Redis, frontend tests/build и online-сборку API image.
Не выполняются полный Ruff/Black check, frontend lint, dependency audit,
Compose smoke test и deploy; последний должен оставаться отдельным job с
явным environment approval.

**TLS** в nginx не терминируется. Production overlay запускает Caddy с
автоматическим HTTPS по домену из `deploy/Caddyfile`; подробные шаги и порты —
в [deploy.md](./deploy.md). DNS, доступность 80/443 и действующий сертификат на
VPS не проверялись. Для другого ingress замени Caddy и закрой прямой доступ к
origin.

**Почта:** без SMTP/Resend письма пишутся в `storage/emails/` только вне production. В production provider обязателен при запуске; SMTP использует STARTTLS или implicit TLS, plaintext запрещён.

**Наблюдаемость воркеров:** worker healthcheck подтверждает соединение с
broker, у beat healthcheck отключён. Prometheus server, Alertmanager и log
retention в Compose отсутствуют; перед production необходимо определить
внешний scrape/alerting и ответственного, а не считать `/metrics` готовой
системой мониторинга.

---

## Чего не делать сейчас

Kubernetes и несколько реплик API мало дают, пока CI не собирает online-образ стабильно. Offline-`.venv` не убирать — нужен для сборки без сети.
