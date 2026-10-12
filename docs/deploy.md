# Деплой Landlords

Операционный runbook: поднять стек, проверить готовность, бэкап и восстановление.
Стратегия — [ROADMAP.md](./ROADMAP.md), инфра — [INFRA.md](./INFRA.md).

## Подготовка

1. Скопируй [`.env.example`](../.env.example) в `backend/.env` и при необходимости в корневой `.env` (подстановка `${DB_*}` в compose).
2. Задай уникальный `SECRET_KEY`, `APP_ENV=production`, `DEBUG=false`, `ALLOW_PUBLIC_REGISTRATION=false`.
3. Пароли Postgres/Redis — только из env; в prod-профиле порты БД на хост не публикуются (см. `docker-compose.yml` без override).

Online-сборка образа API (CI / машина с PyPI):

```bash
export INSTALL_MODE=online
docker compose build api
```

Offline (есть локальный `.venv` на Python 3.12):

```bash
export INSTALL_MODE=offline   # default
docker compose build api
```

## Первый запуск

```bash
# без docker-compose.override.yml на VPS (порты БД не открывать):
docker compose -f docker-compose.yml up -d --build

# проверка
curl -sf http://localhost/ready
curl -sf http://localhost/api/v1/  # или открыть SPA на http://localhost/
```

Миграции Alembic накатывает entrypoint сервиса `api` (`RUN_MIGRATIONS=1`). Worker и beat ждут healthy API.

Showcase-демо (портфолио / самопроверка; на публичном VPS смени пароль):

```bash
docker compose exec api python -m app.cli seed-demo
# дефолт: demo@example.com / ChangeMeDemo1!
```

Создаёт пользователя (если нет) и богатые демо-данные. Идемпотентно. Публичный
`POST /v1/auth/register` (через nginx — `/api/v1/auth/register`) при
`ALLOW_PUBLIC_REGISTRATION=false` закрыт; CLI от флага не зависит.

## TLS

Перед публичным доступом поставь сертификат перед nginx (certbot + reverse proxy или Caddy). Пока слушает только порт 80; HSTS на голом HTTP не включай. После HTTPS обнови `FRONTEND_URL` в `backend/.env`.

## Бэкап

Ежедневно (cron на хосте), каталог например `/var/backups/landlords`:

```bash
BACKUP_DIR=/var/backups/landlords
STAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Postgres
docker compose exec -T postgres \
  pg_dump -U "${DB_USER:-postgres}" -d "${DB_NAME:-landlords_db}" -Fc \
  > "$BACKUP_DIR/db_$STAMP.dump"

# Документы (PDF и вложения)
tar -czf "$BACKUP_DIR/documents_$STAMP.tar.gz" -C . storage/documents

# ротация: хранить последние 14 дней
find "$BACKUP_DIR" -type f -mtime +14 -delete
```

## Восстановление

На пустую машину с тем же `docker-compose.yml` и `.env`:

```bash
docker compose -f docker-compose.yml up -d postgres redis
# дождаться healthy postgres

# остановить API/воркеры, чтобы не писали в БД
docker compose -f docker-compose.yml stop api celery-worker celery-beat nginx

# восстановить БД (custom format от pg_dump -Fc)
docker compose exec -T postgres \
  pg_restore -U "${DB_USER:-postgres}" -d "${DB_NAME:-landlords_db}" --clean --if-exists \
  < /path/to/db_YYYYMMDD_HHMMSS.dump

# восстановить документы
tar -xzf /path/to/documents_YYYYMMDD_HHMMSS.tar.gz -C .

docker compose -f docker-compose.yml up -d
curl -sf http://localhost/ready
```

После старта API снова прогонит `alembic upgrade head` (идемпотентно, если схема уже на head).

## Наблюдаемость и поддержка

В `backend/.env` для прода:

```bash
SENTRY_DSN=https://...@sentry.io/...
SUPPORT_EMAIL=hello@landlords.ru
# OPS_DISK_MIN_FREE_MB=500
# OPS_BEAT_STALE_HOURS=26
# STATUS_INCIDENTS_PATH=/app/storage/status/incidents.json
```

Инциденты на публичной странице `/status` правятся без редеплоя — файл на хосте:

```bash
# пример: объявить деградацию
cat > storage/status/incidents.json <<'EOF'
{
  "overall": "degraded",
  "updated_at": "2026-10-05T12:00:00+00:00",
  "incidents": [
    {
      "id": "smtp-2026-10-05",
      "title": "Задержки почты",
      "status": "investigating",
      "started_at": "2026-10-05T11:00:00+00:00",
      "message": "Письма с напоминаниями могут приходить с задержкой."
    }
  ]
}
EOF
```

`overall`: `operational` | `degraded` | `outage`. Volume `./storage/status` смонтирован в api и celery-worker.

Алерты ops уходят на `SUPPORT_EMAIL` и в Sentry (если DSN задан). nginx не
проксирует `/metrics`, поэтому в production-профиле проверяйте endpoint внутри
API-контейнера:

```bash
docker compose exec -T api python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/metrics').read().decode())" \
  | grep '^ops_'
```

В локальном override тот же endpoint доступен как
`http://localhost:8000/metrics`.

## Чеклист перед продом

- [ ] `APP_ENV=production`, свой `SECRET_KEY`
- [ ] `ALLOW_PUBLIC_REGISTRATION=false`
- [ ] Postgres/Redis без `ports` на хост
- [ ] `curl /ready` → 200
- [ ] Пробный dump → restore на чистый volume
- [ ] TLS и корректный `FRONTEND_URL`
- [ ] SMTP (этап 2) или осознанный `ALLOW`/файл для reset только на self-hosted
- [ ] `SENTRY_DSN` и `SUPPORT_EMAIL`
- [ ] `storage/status/incidents.json` на месте
- [ ] Демо-пароль не оставлять дефолтным на публичном хосте
