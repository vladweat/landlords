# Тестирование и проверки

## Backend

CI использует Python 3.12 и устанавливает `backend/requirements.lock`.
`backend/requirements.txt` задаёт прямые зависимости; lock фиксирует их
транзитивное Linux/Python 3.12 окружение.

```bash
cd backend
pytest -q tests/unit tests/tasks
ruff check app tests --select E9,F63,F7,F82
```

Для integration suite используйте только изолированный Compose-стек и явные
`DB_*`/`REDIS_*` значения из раздела ниже.

Unit/services/domain tests в основном используют mocks и не требуют runtime
services. Task tests проверяют Celery use cases/lock. Integration fixtures:

1. подключаются к изолированному PostgreSQL через `MIGRATION_DB_*`;
2. удаляют и создают `landlords_test`, подготавливают runtime role с DML grants
   и отдельную `landlords_rls_resolver` роль;
3. применяют Alembic `head` роль миграций;
4. подменяют FastAPI `get_db_session` на engine рабочую роль;
5. после suite удаляют test database.

Следствие: integration suite требует migration role с правами create/drop database
и create role. Чтобы подготовить resolver-role с `BYPASSRLS`, migration admin
должен быть superuser; сама resolver-role не имеет login и получает только
column-level grants, а runtime role не состоит в ней. Рабочая роль не должна
владеть базой или таблицами.
Она также ожидает Redis для тестируемых путей, хотя не каждый test обращается к
нему. Fixtures регистрируют test user через `/v1/auth/register`, поэтому
`ALLOW_PUBLIC_REGISTRATION` должен быть `true`: скопированный `.env.example`
задаёт `false` и без override ломает setup тестов. Не направляйте suite на
shared/production DB.

После включения Redis ACL (см. создание secret files в
[`configuration.md`](configuration.md)) gated-проверка должна обращаться к Redis внутри
Compose-сети и использовать credentials проверяемого сервиса. Запустите Redis,
затем из корня проекта выполните проверки API и worker identity отдельно:

```bash
docker compose up -d redis
docker compose run --rm --no-deps \
  -e RUN_REDIS_ACL_TESTS=true \
  -v "$PWD/backend/tests:/app/tests:ro" \
  --entrypoint pytest api -q tests/integration/test_redis_acl.py
docker compose run --rm --no-deps \
  -e RUN_REDIS_ACL_TESTS=true \
  -v "$PWD/backend/tests:/app/tests:ro" \
  --entrypoint pytest celery-worker -q tests/integration/test_redis_acl.py
```

Локальный integration suite запускайте только на отдельном тестовом стеке.
`docker-compose.test.yml` создаёт PostgreSQL с временным `tmpfs` и Redis без
ACL на локальных портах `5433` и `6380`:

```bash
docker compose -f docker-compose.test.yml up -d --wait
cd backend
DB_HOST=127.0.0.1 DB_PORT=5433 DB_USER=landlords_runtime \
DB_PASSWORD=runtime-test-secret MIGRATION_DB_USER=postgres \
MIGRATION_DB_PASSWORD=landlords-test-only DB_NAME=landlords_db \
REDIS_HOST=127.0.0.1 REDIS_PORT=6380 ALLOW_PUBLIC_REGISTRATION=true \
  pytest -q tests/integration
cd ..
docker compose -f docker-compose.test.yml down
```

Не подменяйте тестовым suite production/shared database: fixture удаляет и
создаёт базу `landlords_test`. Пароль тестового PostgreSQL можно переопределить
через `TEST_DB_PASSWORD` и `MIGRATION_DB_PASSWORD`; `DB_PASSWORD` задаёт отдельного пользователя приложения.

Healthcheck helpers и ограничения Celery lock проверяются вместе с unit/task
suite. Перед изменением мониторинга проверь Prometheus config и rules, Grafana
JSON и Compose overlay:

```bash
docker run --rm --entrypoint promtool \
  -v "$PWD/deploy/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  -v "$PWD/deploy/monitoring/rules:/etc/prometheus/rules:ro" \
  prom/prometheus:v3.13.3 check config /etc/prometheus/prometheus.yml
docker run --rm --entrypoint promtool \
  -v "$PWD/deploy/monitoring/rules:/etc/prometheus/rules:ro" \
  prom/prometheus:v3.13.3 check rules /etc/prometheus/rules/landlords-alerts.yml
python -m json.tool deploy/monitoring/grafana/dashboards/landlords-overview.json >/dev/null
docker compose -f docker-compose.yml -f docker-compose.production.yml config --quiet
```

Compose config validation требует существующий `backend/.env` и host paths
secret files из корневого `.env`; не заменяйте реальные secrets пустыми файлами
на рабочем сервере. Команда не запускает контейнеры.

## Проверка ingress rate limits

После сборки локальных образов `landlords-nginx`, `landlords-api` и `caddy:2`
запустите из корня репозитория:

```bash
deploy/test-rate-limits.sh
```

Скрипт создаёт временную Docker-сеть и mock API, проверяет лимиты через Caddy и
nginx, затем удаляет свои контейнеры и сеть. Он не использует обычный Compose
volume и не обращается к рабочей БД.

## Frontend

CI использует Node 22:

```bash
cd frontend
npm ci
npm test
npm run build
```

Дополнительная локальная проверка:

```bash
npm run lint
```

`build` выполняет `tsc && vite build`. Vitest tests находятся рядом с source и
имеют suffix `.test.ts[x]`.
