# Конфигурация

Backend использует `pydantic-settings` (`backend/app/core/config.py`):
переменные окружения имеют приоритет над `.env` текущего working directory.
Compose передаёт `backend/.env` сервисам через `env_file` и переопределяет
`DB_HOST=postgres`, `REDIS_HOST=redis`, а также отдельную Redis ACL identity и
путь к password file для каждого сервиса. Корневой `.env` нужен Compose для
подстановки `${DB_*}`, путей `REDIS_*_PASSWORD_FILE` и `REDIS_ACL_FILE`; он не
передаёт приложению общий Redis password.

Ниже указаны defaults из кода, не рекомендуемые production-значения. Шаблон
`.env.example` переопределяет некоторые defaults: например, в коде публичная
регистрация по умолчанию включена, а шаблон оставляет её выключенной.

## Application и безопасность

| Переменная | Default | Назначение |
|---|---:|---|
| `APP_NAME` | `FastAPI DDD Service` | Название OpenAPI |
| `APP_VERSION` | `0.1.0` | Версия API/Sentry release |
| `APP_ENV` | `development` | `development`, `staging` или `production` |
| `DEBUG` | `true` | Включает Swagger, ReDoc и OpenAPI; dev override отдельно запускает uvicorn с reload |
| `ALLOW_PUBLIC_REGISTRATION` | `true` | Разрешает `POST /v1/auth/register` |
| `SECRET_KEY` | development placeholder | Подпись JWT; обязателен уникальный secret в production |
| `FRONTEND_URL` | `http://localhost:3000` | Ссылки в письмах и billing return |
| `SUPPORT_EMAIL` | `hello@landlords.ru` | Получатель feedback/ops alerts |

При неизвестном `APP_ENV` процесс прекращает запуск. При `APP_ENV=production`
процесс также прекращает запуск, если `SECRET_KEY` пуст или равен встроенной
строке `change-me-in-production-change-me`. В `.env.example` задано другое
значение — `change_me`, которое текущая проверка принимает. Его нужно заменить
уникальным случайным ключом вручную; исправление расхождения зарегистрировано в
[техническом долге](../maintenance/technical-debt.md). Значения из `.env.example`
— только локальные примеры.

## PostgreSQL

| Переменная | Default | Формат/примечание |
|---|---:|---|
| `DB_HOST` | `localhost` | hostname |
| `DB_PORT` | `5432` | integer |
| `DB_USER` | `postgres` | username |
| `DB_PASSWORD` | `postgres` | secret |
| `DB_NAME` | `landlords_db` | database |
| `DB_POOL_SIZE` | `20` | постоянные connections на process |
| `DB_MAX_OVERFLOW` | `40` | дополнительные connections |
| `DB_POOL_PRE_PING` | `true` | проверка connection перед выдачей |
| `DB_ECHO` | `false` | SQL logging; не включать без необходимости |

`DATABASE_URL` вычисляется, отдельная переменная `DATABASE_URL` не читается.
При нескольких API/worker processes учитывайте pool на каждый process.

## Redis и Celery

| Переменная | Default | Назначение |
|---|---:|---|
| `REDIS_HOST` | `localhost` | Redis hostname |
| `REDIS_PORT` | `6379` | port |
| `REDIS_DB` | `0` | logical DB |
| `REDIS_USERNAME` | unset | именованная Redis ACL identity; Compose задаёт отдельно для каждого service |
| `REDIS_PASSWORD_FILE` | unset | path к read-only secret file; содержимое не читается в logs |
| `REDIS_PASSWORD` | unset | локальная совместимость; production Compose использует password files |
| `REDIS_KEY_PREFIX` | `landlords:` | namespace для Celery, locks и ops keys |
| `CELERY_TASK_DEFAULT_QUEUE` | `default` | queue |
| `CELERY_TASK_SOFT_TIME_LIMIT` | `300` | seconds |
| `CELERY_TASK_TIME_LIMIT` | `600` | seconds |
| `CELERY_WORKER_MAX_TASKS_PER_CHILD` | `1000` | recycle threshold |

Transactional outbox управляется отдельным `outbox-relay` process. Terminal
failure rows сохраняются для операторской проверки.

| Переменная | Default | Назначение |
|---|---:|---|
| `OUTBOX_RELAY_POLL_SECONDS` | `2` | Интервал опроса PostgreSQL |
| `OUTBOX_RELAY_BATCH_SIZE` | `50` | Верхняя граница одной claim-пачки |
| `OUTBOX_RELAY_LEASE_SECONDS` | `300` | Срок claim до повтора dispatch |
| `OUTBOX_RELAY_MAX_ATTEMPTS` | `12` | Предел брокерных dispatch attempts |
| `OUTBOX_RELAY_BASE_BACKOFF_SECONDS` | `2` | Базовая экспоненциальная задержка с jitter |
| `OUTBOX_RELAY_MAX_BACKOFF_SECONDS` | `300` | Верхняя граница backoff |
| `OUTBOX_TASK_MAX_FAILURES` | `5` | Число task failures до terminal failure |

`REDIS_URL`, broker и result backend вычисляются; отдельные
`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` не используются. Обычный dev
Compose не публикует Redis port на host. Для local Python используйте Redis с
доступным host port и настройте соответствующие `REDIS_HOST`/`REDIS_PORT` и
credentials; изолированный тестовый стек на `127.0.0.1:6380` работает без ACL.

Compose использует Redis 7 ACL file и отдельные host-only password files для
API, worker, beat, outbox-relay и Flower. Файл ACL хранит только SHA-256
password hashes; raw passwords доступны приложению через read-only Docker
secrets. Переменные `REDIS_ACL_FILE`, `REDIS_API_PASSWORD_FILE`,
`REDIS_WORKER_PASSWORD_FILE` и `REDIS_FLOWER_PASSWORD_FILE` задают host paths
в корневом `.env`.

Создайте password files с правами `0600`, сгенерируйте независимые случайные
пароли и поместите их SHA-256 hashes в ACL file. Не копируйте секреты в
репозиторий. ACL users: `landlords_api` имеет доступ
к `landlords:ops:*`; worker, beat, outbox-relay и Flower ограничены ключами `landlords:*` и
каналами `landlords:/0.celery.pidbox` и `landlords:celery-task-meta-*`; worker
дополнительно использует pattern `landlords:/0.celeryev/worker.*`, Flower —
`landlords:/0.celeryev/*`. Kombu применяет
`global_keyprefix=landlords:` и к ключам, и к аргументам Pub/Sub-команд; с
Redis ACL pattern для `PSUBSCRIBE` должен совпадать с переданным channel pattern.
При изменении `REDIS_KEY_PREFIX` передайте то же значение provision-скрипту через
`--key-prefix` или переменную окружения;
`landlords_health`
имеет пустой пароль, key/channel access закрыт, разрешён только `PING`;
`default` выключен. Production требует username и читаемый password file. Для локальной
изолированной конфигурации вне production можно оставить credentials пустыми,
если локальный Redis запущен без ACL.

Для первой локальной или production-настройки из корня репозитория выполните:

```bash
cd backend
python -m app.scripts.provision_redis_acl --output-dir ../secrets/redis
cd ..
```

Команда создаёт независимые credentials и hash-only ACL file без вывода
паролей. Она откажется перезаписывать существующие secret files. Для обновления
правил ACL без ротации паролей используйте `--refresh-acl`; не запускайте это
во время подключения работающих сервисов без согласованного окна обслуживания.

## Email

| Переменная | Default | Назначение |
|---|---:|---|
| `SMTP_HOST` | unset | Явный SMTP; при наличии приоритетнее Resend |
| `SMTP_PORT` | `587` / `465` / `25` | Default зависит от `SMTP_TLS_MODE`: STARTTLS / implicit TLS / plaintext dev |
| `SMTP_TLS_MODE` | `starttls` | `starttls`, `ssl` или `none`; production запрещает `none` |
| `SMTP_USER` | unset | login |
| `SMTP_PASSWORD` | unset | secret |
| `SMTP_FROM` | `no-reply@example.com` | envelope/header From |
| `RESEND_API_KEY` | unset | Используется как SMTP password |

Без SMTP/Resend письма пишутся относительно working directory в
`storage/emails/` только вне production. В production отсутствие provider или
ошибка доставки приводит к исключению; production startup завершается ошибкой,
если provider не задан или выбран `SMTP_TLS_MODE=none`. STARTTLS handshake error не игнорируется
и plaintext повторной отправки не происходит. Для `SMTP_TLS_MODE=ssl` используется
SMTP_SSL с проверкой сертификата; для `starttls` сертификат также проверяется.

## Billing и внешние сервисы

| Переменная | Default | Назначение |
|---|---:|---|
| `YOOKASSA_SHOP_ID` | unset | YooKassa shop identifier |
| `YOOKASSA_SECRET_KEY` | unset | secret |
| `YOOKASSA_RETURN_URL` | `${FRONTEND_URL}/settings?billing=return` | redirect |
| `BILLING_PRO_PRICE_RUB` | `990` | integer RUB/month |
| `BILLING_GRACE_DAYS` | `3` | integer days |
| `SENTRY_DSN` | unset | Sentry DSN; чувствительное значение |

Если пара YooKassa credentials неполна, checkout считается выключенным.

## Storage, ops и logging

| Переменная | Default | Назначение |
|---|---:|---|
| `DOCUMENTS_STORAGE_DIR` | `/app/storage/documents` | Файлы документов |
| `STATUS_INCIDENTS_PATH` | `/app/storage/status/incidents.json` | Публичный status |
| `OPS_DISK_MIN_FREE_MB` | `500` | Порог alert |
| `OPS_BEAT_STALE_HOURS` | `26` | Порог stale heartbeat |
| `LOG_LEVEL` | `INFO` | Уровень |

## Runtime/build переменные вне `Settings`

| Переменная | Компонент | Назначение |
|---|---|---|
| `INSTALL_MODE` | Docker build | `offline` копирует `.venv`; `online` запускает pip |
| `RUN_MIGRATIONS` | entrypoint | при `1` выполняет `alembic upgrade head` |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | official Postgres image | задаются из `${DB_*}` Compose |

## Безопасный production minimum

Пример показывает параметры приложения, а не полный deployment manifest.
`APP_ENV=production` также требует почтового provider и Redis credentials;
Compose задаёт отдельные Redis ACL username и secret file для каждого сервиса.
Значение `change_me` из `.env.example` — локальный placeholder: замените его
уникальным случайным ключом до запуска production.

```env
APP_ENV=production
DEBUG=false
ALLOW_PUBLIC_REGISTRATION=false
SECRET_KEY=<случайное длинное значение>
FRONTEND_URL=https://example.invalid
DB_PASSWORD=<отдельный сильный пароль>
SMTP_HOST=<smtp-host>
SMTP_TLS_MODE=starttls
```

Не помещайте реальные значения в команды, docs, CI logs или Git. После смены
`SECRET_KEY` все JWT/reset tokens становятся недействительны.
