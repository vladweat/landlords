# Деплой Landlords

Операционный runbook: поднять стек, проверить готовность, бэкап и восстановление.

## Подготовка

1. Скопируй [`.env.example`](../.env.example) в `backend/.env` и корневой `.env`; Compose читает из корневого файла `${DB_*}` и пути к host-only secrets.
2. В `backend/.env` задай уникальный `SECRET_KEY`, `APP_ENV=production`, `DEBUG=false`, `ALLOW_PUBLIC_REGISTRATION=false`, email provider (`SMTP_HOST` или `RESEND_API_KEY`) и `SMTP_TLS_MODE=starttls` либо `ssl`.
3. Создай отдельные Redis password files и ACL file согласно [configuration guide](development/configuration.md). Redis ACL file хранит hashes; passwords не передаются через env, Git, logs или синхронизацию.
4. Настрой отдельные `DB_USER`/`DB_PASSWORD` для runtime-роли и `MIGRATION_DB_USER`/`MIGRATION_DB_PASSWORD` для роли миграций. Секрет миграционной роли хранится в корневом `.env`; Compose передаёт его только one-shot сервисам подготовки роли и миграции. Redis использует secret files; порты БД/Redis не публикуются на host.

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
# На публичной VPS используй production overlay: Caddy публикует порты 80/443,
# nginx остаётся только во внутренней Compose-сети. DNS из deploy/Caddyfile
# должен указывать на сервер.
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d --build

# проверка nginx изнутри его контейнера
docker compose -f docker-compose.yml -f docker-compose.production.yml exec nginx curl -sf http://localhost/ready
# проверка публичного маршрута после настройки DNS и получения сертификата
curl -sf https://landlords.wvzl.site/ready
```

Перед применением ingress-конфигурации smoke test
`deploy/test-rate-limits.sh` поднимает временную Docker-сеть с mock API, nginx и
Caddy. Он проверяет разные client IP, поддельный `X-Forwarded-For`, JSON `429`,
неограниченные health/status пути и отсутствие capability-token paths в nginx
logs; после завершения удаляет только созданные им контейнеры и сеть.

Перед изменением существующей БД создай и проверь backup. Первый запуск выполняет
one-shot `db-role-bootstrap`, затем `db-migrate`; API и Celery используют
непривилегированную runtime-роль и стартуют после успешной миграции. Для
существующего Postgres volume `POSTGRES_USER` и `POSTGRES_PASSWORD` не меняют роли
в базе. `MIGRATION_DB_USER`/`MIGRATION_DB_PASSWORD` должны принадлежать
PostgreSQL superuser: bootstrap создаёт `landlords_rls_resolver` с `BYPASSRLS`,
но без login и DDL-привилегий, и переводит на неё только узкие resolver-функции.
Укажи новые runtime credentials в `DB_USER`/`DB_PASSWORD`, затем запусти
`docker compose run --rm db-role-bootstrap`, после него
`docker compose run --rm db-migrate`; команды не очищают volume. После миграции
проверь `/ready` и tenant/auth smoke tests, затем перезапусти стек, чтобы
API/worker подключились runtime-ролью. Не удаляй migration credentials до
проверки rollback-процедуры.

## Модель API процессов

Каждый API container запускает один Uvicorn process. Масштабирование выполняй
числом контейнеров за ingress/load balancer; не добавляй Gunicorn worker pool в
образ. При этой модели Prometheus собирает обычные process-local `/metrics` с
каждой replica, multiprocess mode не нужен. Перед запуском нескольких replicas
настрой обнаружение всех контейнеров в ingress и рассчитай PostgreSQL pool на
число экземпляров: текущие `DB_POOL_SIZE=20` и `DB_MAX_OVERFLOW=40` дают до 60
соединений на process при `max_connections=100`.

## Локальный synthetic showcase

`seed-demo` содержит фиксированные synthetic credentials
`demo@example.com / ChangeMeDemo1!`. Команда отказывает до подключения к БД,
если `APP_ENV` не равен `demo` или `DB_NAME` не равен `landlords_demo`. Не
запускай её в обычной development/production Compose-среде.

Из корня репозитория подними отдельный стек. Он использует Compose project
`landlords-demo`, собственные PostgreSQL и storage volumes, отдельную internal
network без внешнего выхода, публикует API только на loopback и не монтирует
`storage/documents` или `backend/.env`. В нём нет Celery workers, а provider и
email credentials пусты.

```bash
docker compose --project-name landlords-demo -f docker-compose.demo.yml up -d --build
docker compose --project-name landlords-demo -f docker-compose.demo.yml exec api \
  python -m app.cli seed-demo
```

Для доступа открой `http://127.0.0.1:8001/docs`, выполни `POST /v1/auth/login`
с указанными credentials и просмотри `GET /v1/properties`, `GET /v1/tenants`,
`GET /v1/contracts` и `GET /v1/contracts/{contract_id}/ledger`. Публичная
регистрация в demo выключена; CLI создаёт только synthetic demo account внутри
этой БД. YooKassa checkout и внешняя почта не настроены.

Seed повторяем: повторный запуск не добавляет записи. Он создаёт property
«Арбат, 15», tenant «Анна Смирнова», активный договор с месячной арендой
75 000 RUB, rent charges и ручную частичную оплату 37 500 RUB. Открой ledger
этого договора, чтобы увидеть начисления, payment и остаток. Все данные
искусственные; demo documents volume изначально пуст.

Остановить стек, сохранив данные:

```bash
docker compose --project-name landlords-demo -f docker-compose.demo.yml down
```

Сбросить только demo containers и их volumes (операция удаляет synthetic DB и
demo storage; перед запуском проверь project name):

```bash
deploy/reset-demo.sh --confirm
```

## TLS

`nginx/nginx.conf` слушает только HTTP port 80. Для публичного topology в
репозитории есть `docker-compose.production.yml`: он запускает Caddy с
`deploy/Caddyfile`, где настроены `landlords.wvzl.site`, HTTPS, redirect и HSTS;
nginx не публикует host port и доступен Caddy по DNS имени сервиса во внутренней
сети. Caddy имеет фиксированный адрес `172.18.0.10`. Перед запуском проверь,
что Docker subnet `172.18.0.0/16` свободен; динамические адреса пула
резервируются в `172.18.128.0/17`. Для другого домена измени site address в
Caddyfile. Перед публичным доступом проверь DNS и доступность входящих портов
80/443, затем:

- принимает только HTTPS, перенаправляет HTTP на HTTPS и включает HSTS после
  проверки домена/сертификата;
- передаёт запросы nginx только через внутреннюю Compose-сеть, не публикуя origin;
- nginx принимает forwarded client IP только от фиксированного Caddy peer;
  не добавляй в `set_real_ip_from` всю Docker-подсеть или публичные диапазоны;
- nginx ограничивает auth, регистрацию, принятие приглашений, публичные claims и
  создание напоминаний; публичный клиент не может выбрать IP лимитера через
  собственный `X-Forwarded-For`;
- задаёт `FRONTEND_URL` ровно публичному HTTPS origin, используемому браузером;
- исключает capability URL и query tokens из access logs, analytics и tracing.

В production `APP_ENV=production` устанавливает Secure cookie независимо от
внутренней схемы HTTP между ingress и Compose. Локальный override сохраняет
HTTP-порты для разработки; не запускай его на публичном сервере.

### Проверка и откат ingress changes

Перед запуском новой конфигурации проверь Compose overlay, Caddyfile и nginx:

```bash
docker compose -f docker-compose.yml -f docker-compose.production.yml config --quiet
docker run --rm -v "$PWD/deploy/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2 caddy validate --config /etc/caddy/Caddyfile
deploy/test-rate-limits.sh
```

Изменения доверенного proxy IP и nginx rate zones выпускай вместе. Если smoke
test не проходит, верни предыдущие `deploy/Caddyfile`, `nginx/nginx.conf` и
Compose overlay одним релизом; не оставляй nginx доверять адресу, которого
Caddy больше не использует, и не расширяй `set_real_ip_from` для обхода ошибки.

## Мониторинг

Создай дополнительные host-only password files до запуска Compose. Каталог
`secrets/` не добавляй в Git:

```bash
install -d -m 0700 secrets secrets/postgres secrets/monitoring
umask 077
openssl rand -hex 32 > secrets/postgres/exporter.password
openssl rand -hex 32 > secrets/monitoring/grafana_admin.password
chmod 0644 secrets/postgres/exporter.password secrets/monitoring/grafana_admin.password
```

Redis ACL provision-скрипт генерирует отдельный пароль `landlords_exporter`
и JSON password map для redis_exporter.
PostgreSQL роль создаёт `db-role-bootstrap`; она имеет `CONNECT` к прикладной
базе и членство `pg_monitor`, но не получает grants на таблицы приложения.
Grafana получает admin пароль из secret file. Не передавай пароли через
environment variables или аргументы команд. Каталоги с secret files должны
оставаться `0700`: Compose монтирует file-backed secrets как bind mounts и
сохраняет права исходных файлов, поэтому mode `0644` безопасен только внутри
недоступного другим host users каталога.

Prometheus, Alertmanager и exporter endpoints остаются только во внутренней
Compose-сети. Grafana публикуется на `127.0.0.1:3000`; доступ с рабочей машины
открой SSH-туннелем:

```bash
ssh -L 3001:127.0.0.1:3000 user@server
```

Затем открой `http://127.0.0.1:3001`. Prometheus хранит метрики максимум 15 дней
и ограничивает TSDB 4 GB; именованные volumes Prometheus, Grafana и Alertmanager
сохраняются при обычном rollback или `docker compose down` без `-v`. Текущий
Alertmanager группирует полученные alerts локально; внешний email/webhook receiver
нужно настроить отдельно, прежде чем полагаться на доставку уведомлений.

Prometheus rule-файл и dashboard загружаются из репозитория при старте сервисов.
После подготовки secret files обнови стек обычной командой Compose с production
overlay, затем проверь состояние и логи:

```bash
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d
docker compose -f docker-compose.yml -f docker-compose.production.yml ps
docker compose -f docker-compose.yml -f docker-compose.production.yml logs --tail=100 prometheus grafana alertmanager
```

Healthchecks worker/beat/relay показывают состояние в `docker compose ps`.
Dashboard `Landlords overview` содержит доступность API и exporters, ресурсы
хоста и документов, PostgreSQL, Redis, события Celery, плановую проверку, relay и
outbox. Алерты и их `for` интервалы описаны в
[`background-jobs.md`](architecture/background-jobs.md#healthchecks-и-метрики).
App-level alerts о диске и активности beat также идут на `SUPPORT_EMAIL` и в
Sentry; Prometheus Alertmanager сейчас не имеет внешнего receiver.

При откате к предыдущему коду верни соответствующие версии Compose и файлов
мониторинга, затем подними прежний стек без удаления volumes. Не используй
`docker compose down -v`: это удалит историю Prometheus, состояние Grafana и
Alertmanager. Host-only secret files также нужны старой конфигурации, пока
работают monitoring services. `/metrics` доступен только из API/внутренней сети;
nginx отдаёт по внешнему `/metrics` SPA, а не Prometheus exposition.

## Резервные копии

Репозиторий содержит `deploy/backup-landlords.sh` и systemd units. После
установки и включения units по процедуре ниже timer запускает backup ежедневно
в 02:30 UTC с задержкой до 5 минут. Комплект в
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
только созданные им контейнер и volume.

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
- [ ] Не запускать synthetic `seed-demo` в production; production CLI guard должен отклонять вызов
- [ ] Перед публикацией обновлённой landing page отключить или сменить пароль
  ранее опубликованного demo-аккаунта, если он существует; его production-состояние
  нужно проверить отдельно
