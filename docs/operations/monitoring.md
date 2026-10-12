# Наблюдаемость

## Health endpoints

| Endpoint | Проверка | Использование |
|---|---|---|
| `/health` | FastAPI отвечает | liveness |
| `/ready` | `SELECT 1` и Redis `PING` | readiness/nginx health |
| `/metrics` | Prometheus text | scrape напрямую из API/internal network |
| `/api/v1/public/status` | JSON из incidents file | пользовательский status |

Stale beat и ops gauges обновляются во время `/ready`, но ошибка ops check не
меняет 200, если DB/Redis доступны. `/metrics` не имеет auth и не проксируется
явным nginx location; при публикации добавьте network/access policy.

## Логи

`LoggingMiddleware` пишет вход/выход, method, path, query, client IP, status,
latency и `request_id`; response содержит `X-Request-ID`. Celery использует task
logger. Не передавайте secrets/tokens в query string: query логируется.

`LOG_LEVEL` используется uvicorn entry path; `LOG_FORMAT` объявлен, но
централизованная настройка Loguru JSON sink в просмотренном коде отсутствует.
Compose полагается на container stdout/stderr и не задаёт rotation policy.

```bash
docker compose logs --since=30m api nginx
docker compose logs --since=30m celery-worker celery-beat
```

## Метрики и Sentry

`prometheus_client` экспортирует process/default metrics, Celery task counter и
ops gauges (beat timestamp, free disk). Sentry включается при `SENTRY_DSN` для
FastAPI/Celery/SQLAlchemy; traces sample rate — 0.1 в production и 0 иначе.

В репозитории нет Prometheus server, dashboard, Alertmanager или log backend.
Ops alerts отправляются на `SUPPORT_EMAIL` и в Sentry при настройке. Порог
диска — `OPS_DISK_MIN_FREE_MB`, stale beat — `OPS_BEAT_STALE_HOURS`.

## Status incidents

`STATUS_INCIDENTS_PATH` — JSON-файл, читаемый `StatusService`. Volume
`storage/status` смонтирован в API и worker. Допустимые значения и безопасный
пример находятся в [deploy.md](../deploy.md).

## Минимальная диагностика

```bash
curl -i http://localhost/health
curl -i http://localhost/ready
curl -s http://localhost:8000/metrics
docker compose ps
docker compose exec postgres pg_isready -U "${DB_USER:-postgres}"
docker compose exec redis redis-cli ping
```

Не включайте debug/SQL logging длительно в production: оно повышает объём
логов и риск записи чувствительных business data.
