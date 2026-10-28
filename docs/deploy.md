# Деплой Landlords

Операционный runbook: поднять стек, проверить готовность, бэкап и восстановление.
Стратегия — [ROADMAP.md](./ROADMAP.md), инфра — [INFRA.md](./INFRA.md).

## Подготовка

1. Скопируй [`.env.example`](../.env.example) в `backend/.env` и корневой `.env`; Compose читает из корневого файла `${DB_*}` и пути к host-only Redis secrets.
2. В `backend/.env` задай уникальный `SECRET_KEY`, `APP_ENV=production`, `DEBUG=false`, `ALLOW_PUBLIC_REGISTRATION=false`, email provider (`SMTP_HOST` или `RESEND_API_KEY`) и `SMTP_TLS_MODE=starttls` либо `ssl`.
3. Создай отдельные Redis password files и ACL file согласно [configuration guide](development/configuration.md). Redis ACL file хранит hashes; passwords не передаются через env, Git, logs или синхронизацию.
4. Пароли Postgres задаются env, Redis — secret files; в prod-профиле порты БД/Redis на host не публикуются (см. `docker-compose.yml` без override).

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

Frontend собирается на VM вне Docker; nginx image копирует готовый `frontend/dist`
и не скачивает npm-пакеты. Перед первым запуском и после изменений frontend:

```bash
cd frontend
npm run build
cd ..
docker compose build --pull=false nginx
```

На VM должны быть установлены Node.js/npm и зависимости из `frontend/package-lock.json`.
Для текущего Vite нужен Node.js 20.19+ или 22.12+.

## Первый запуск

```bash
# На публичной VPS используй production overlay: он добавляет Caddy и
# привязывает nginx к localhost:8080. DNS из deploy/Caddyfile должен указывать
# на сервер, входящие порты 80 и 443 должны быть доступны.
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d --build

# проверка локального nginx origin из хоста
curl -sf http://127.0.0.1:8080/ready
# проверка публичного маршрута после настройки DNS и получения сертификата
curl -sf https://landlords.wvzl.site/ready
```

Миграции Alembic накатывает entrypoint сервиса `api` (`RUN_MIGRATIONS=1`). Worker и beat ждут healthy API.

## Модель API процессов

Каждый API container запускает один Uvicorn process. Масштабирование выполняй
числом контейнеров за ingress/load balancer; не добавляй Gunicorn worker pool в
образ. При этой модели Prometheus собирает обычные process-local `/metrics` с
каждой replica, multiprocess mode не нужен. Перед запуском нескольких replicas
настрой обнаружение всех контейнеров в ingress и рассчитай PostgreSQL pool на
число экземпляров: текущие `DB_POOL_SIZE=20` и `DB_MAX_OVERFLOW=40` дают до 60
соединений на process при `max_connections=100`.

Создать демо-данные:

```bash
docker compose exec api python -m app.cli seed-demo
# дефолт: demo@example.com / ChangeMeDemo1!
```

Создаёт пользователя (если нет) и богатые демо-данные. Идемпотентно. Публичный
`POST /v1/auth/register` (через nginx — `/api/v1/auth/register`) при
`ALLOW_PUBLIC_REGISTRATION=false` закрыт; CLI от флага не зависит.

## TLS

`nginx/nginx.conf` слушает только HTTP port 80. Для публичного topology в
репозитории есть `docker-compose.production.yml`: он запускает Caddy с
`deploy/Caddyfile`, где настроены `landlords.wvzl.site`, HTTPS, redirect и HSTS;
nginx доступен Caddy через `127.0.0.1:8080`. Для другого домена измени site
address в Caddyfile. Перед публичным доступом проверь DNS и доступность входящих
портов 80/443, затем:

- принимает только HTTPS, перенаправляет HTTP на HTTPS и включает HSTS после
  проверки домена/сертификата;
- передаёт запросы на локальный nginx origin, не публикуя origin в Internet;
- задаёт `FRONTEND_URL` ровно публичному HTTPS origin, используемому браузером;
- исключает capability URL и query tokens из access logs, analytics и tracing.

В production `APP_ENV=production` устанавливает Secure cookie независимо от
внутренней схемы HTTP между ingress и Compose. Локальный override сохраняет
HTTP-порты для разработки; не запускай его на публичном сервере.

## Резервные копии

Репозиторий содержит `deploy/backup-landlords.sh` и systemd units. После
установки и включения units по процедуре ниже timer запускает backup ежедневно
в 02:30 UTC с задержкой до 5 минут. Это описание конфигурации в репозитории;
установка units и последнее выполнение на VPS не проверялись. Комплект в
`/var/backups/landlords/` содержит
custom dump PostgreSQL, архив `storage/documents`, SHA-256 manifest и маркер
завершения. Запись идёт атомарно во временный каталог; хранятся последние 14
дней завершённых комплектов. Файлы доступны только root (каталог `0700`, файлы
`0600`). В комплект не включаются `.env` или Redis secrets.
Для Docker-команд используется production overlay, если он есть; без него
скрипт работает с базовым `docker-compose.yml` и тем же Compose project name.

После установки и включения второго timer каждое воскресенье в 04:00 UTC он восстанавливает
последнюю копию в отдельный временный PostgreSQL 15 container без сети и
опубликованных портов, проверяет таблицы и архив документов, затем удаляет
только созданные им контейнер и volume. Проверка не останавливает production
сервисы и не подтверждает восстановление всего приложения.

Проверить расписание и последний запуск:

```bash
systemctl list-timers 'landlords-*'
systemctl status landlords-backup.timer landlords-restore-check.timer
systemctl status landlords-backup.service landlords-restore-check.service
journalctl -u landlords-backup.service -n 100 --no-pager
journalctl -u landlords-restore-check.service -n 100 --no-pager
ls -l /var/backups/landlords
```

Первоначальная настройка на VPS:

```bash
# Выполняйте команды из корня checkout (например, /srv/landlords).
cat > /etc/landlords-backup.conf <<'EOF'
PROJECT_DIR=/srv/landlords
BACKUP_DIR=/var/backups/landlords
RETENTION_DAYS=14
MIN_FREE_MB=256
EOF
chown root:root /etc/landlords-backup.conf
chmod 0600 /etc/landlords-backup.conf
install -o root -g root -m 0644 deploy/landlords-backup.service deploy/landlords-backup.timer \
  deploy/landlords-restore-check.service deploy/landlords-restore-check.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now landlords-backup.timer landlords-restore-check.timer
systemctl start landlords-backup.service
systemctl start landlords-restore-check.service
```

Эти копии находятся на той же VPS и не спасут при потере её диска или инстанса.
Off-site S3-compatible storage пока не подключено. PostgreSQL dump и файловый
архив снимаются последовательно при работающем приложении; изменения документов
во время backup могут попасть в разные моменты времени. Для строгой согласованной
копии понадобится короткое окно остановки записывающих сервисов или storage,
поддерживающий snapshot.

## Восстановление на чистую машину

Этот сценарий предназначен для новой VPS с восстановленными `.env`, Redis
secrets и production Compose-файлами. Существующие рабочие volumes он не очищает.
Сначала подними только PostgreSQL, дождись готовности, затем восстанови архив в
созданную Postgres пустую базу `POSTGRES_DB`:

```bash
BACKUP_SET=/var/backups/landlords/landlords-YYYYMMDDTHHMMSSZ
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d postgres
DB_USER=$(docker compose -f docker-compose.yml -f docker-compose.production.yml exec -T postgres printenv POSTGRES_USER)
DB_NAME=$(docker compose -f docker-compose.yml -f docker-compose.production.yml exec -T postgres printenv POSTGRES_DB)
until docker compose -f docker-compose.yml -f docker-compose.production.yml \
  exec -T postgres pg_isready -U "$DB_USER" -d "$DB_NAME"; do sleep 2; done
docker compose -f docker-compose.yml -f docker-compose.production.yml exec -T postgres \
  pg_restore -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl < "$BACKUP_SET/database.dump"
mkdir -p storage
tar -xzf "$BACKUP_SET/documents.tar.gz" -C storage
```

На новой машине сначала убедись, что целевая база пуста. Не используй `--clean`
или `--if-exists` для восстановления в существующую рабочую базу. После
восстановления запусти весь Compose-стек; API выполнит `alembic upgrade head`.
Затем проверь `/ready` и вход в приложение.

## Наблюдаемость и поддержка

В `backend/.env` для прода:

```bash
SENTRY_DSN=https://...@sentry.io/...
SUPPORT_EMAIL=ops@example.org # замени адресом поддержки проекта
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
  "updated_at": "<UTC timestamp, for example 2026-10-28T12:00:00+00:00>",
  "incidents": [
    {
      "id": "smtp-delay-<date>",
      "title": "Задержки почты",
      "status": "investigating",
      "started_at": "<UTC timestamp>",
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
- [ ] SMTP/Resend provider настроен; production SMTP работает через STARTTLS или implicit TLS
- [ ] `SENTRY_DSN` и `SUPPORT_EMAIL`
- [ ] `storage/status/incidents.json` на месте
- [ ] Демо-пароль не оставлять дефолтным на публичном хосте
