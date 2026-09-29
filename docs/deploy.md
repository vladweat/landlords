# Деплой Landlords

Операционный runbook: поднять стек, проверить готовность, бэкап и восстановление.
Стратегия — [ROADMAP.md](./ROADMAP.md), инфра — [INFRA.md](./INFRA.md).

## Подготовка

1. Скопируй [`.env.example`](../.env.example) в `backend/.env` и при необходимости в корневой `.env` (подстановка `${DB_*}` в compose).
2. Задай уникальный `SECRET_KEY`, `APP_ENV=production`, `DEBUG=false`.
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

Демо-аккаунт (не для продакшена):

```bash
docker compose exec api python -m app.cli seed \
  --email demo@example.com \
  --password 'ChangeMeDemo1!'
```

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

## Чеклист перед продом

- [ ] `APP_ENV=production`, свой `SECRET_KEY`
- [ ] Postgres/Redis без `ports` на хост
- [ ] `curl /ready` → 200
- [ ] Пробный dump → restore на чистый volume
- [ ] TLS и корректный `FRONTEND_URL`
- [ ] SMTP (этап 2) или осознанный `ALLOW`/файл для reset только на self-hosted
