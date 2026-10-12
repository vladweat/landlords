# Landlords — инфраструктура и деплой

Локальный и VPS-стек на Docker Compose. Операционный runbook — [deploy.md](./deploy.md). Портфолио — [PORTFOLIO.md](./PORTFOLIO.md).

Продуктовый порядок: [ROADMAP.md](./ROADMAP.md) · чеклист: [PRIORITIES.md](./PRIORITIES.md).

---

## Что уже есть

В `docker-compose.yml`: API, Celery worker и beat, Postgres 15, Redis 7, nginx (SPA + `/api`). Flower — профиль `development`. У API: `/health`, `/ready` (БД + Redis), `/metrics`. Sentry и Prometheus-клиент подключены. Документы — volume `storage/documents`. Override для разработки монтирует исходники и `--reload`.

**Сборка API** — два режима через `INSTALL_MODE`:

| Режим | Когда | Как |
|-------|-------|-----|
| `offline` (default) | нет PyPI на машине сборки | копирует `.venv` (Python 3.12) |
| `online` | CI / чистая машина | `pip install -r requirements.txt` |

Entrypoint API при `RUN_MIGRATIONS=1` гоняет `alembic upgrade head`. Healthcheck смотрит на `/ready`.

**Один вход в prod-профиле:** nginx отдаёт собранный фронт (multi-stage в `nginx/Dockerfile`) и проксирует API. Postgres/Redis без `ports` на хост (порты только в override). `.env.example` с комментариями; `SECRET_KEY` по умолчанию запрещён при `APP_ENV=production`.

**Публичная регистрация** управляется `ALLOW_PUBLIC_REGISTRATION` (для портфолио/прода — `false`). Bootstrap через CLI: `python -m app.cli seed-demo`.

**Данные:** процедура бэкапа/restore — в [deploy.md](./deploy.md). Ops-алерты (beat stale, диск документов) и публичный `/status` — см. тот же runbook.

---

## Что ещё улучшить

**CI** (`.github/workflows/ci.yml`) выполняет critical Ruff checks, unit/tasks,
integration с PostgreSQL/Redis, frontend tests/build и online-сборку API image.
Не выполняются полный Ruff/Black check, frontend lint, dependency audit,
Compose smoke test и deploy; последний должен оставаться отдельным job с
явным environment approval.

**TLS** в compose нет: перед публичным доступом — certbot/Caddy перед nginx, затем корректный `FRONTEND_URL`.

**Почта:** без SMTP/Resend письма пишутся в `storage/emails/`. Для прода задать SMTP или Resend.

**Наблюдаемость воркеров:** worker healthcheck подтверждает соединение с
broker, у beat healthcheck отключён. Prometheus server, Alertmanager и log
retention в Compose отсутствуют; перед production необходимо определить
внешний scrape/alerting и ответственного, а не считать `/metrics` готовой
системой мониторинга.

---

## Чего не делать сейчас

Kubernetes и несколько реплик API мало дают, пока CI не собирает online-образ стабильно. Offline-`.venv` не убирать — нужен для сборки без сети.
