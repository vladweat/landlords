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

1. подключаются к PostgreSQL из `DB_*`;
2. удаляют и создают `landlords_test`;
3. применяют Alembic `head`;
4. подменяют FastAPI `get_db_session`;
5. после suite удаляют test database.

Следствие: integration suite требует PostgreSQL и права create/drop database.
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
DB_HOST=127.0.0.1 DB_PORT=5433 DB_USER=postgres \
DB_PASSWORD=landlords-test-only DB_NAME=landlords_db \
REDIS_HOST=127.0.0.1 REDIS_PORT=6380 ALLOW_PUBLIC_REGISTRATION=true \
  pytest -q tests/integration
cd ..
docker compose -f docker-compose.test.yml down
```

Не подменяйте тестовым suite production/shared database: fixture удаляет и
создаёт базу `landlords_test`. Пароль тестового PostgreSQL можно переопределить
через `TEST_DB_PASSWORD` в Compose и `DB_PASSWORD` для pytest.

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
