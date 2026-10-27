# Тестирование и проверки

## Backend

CI использует Python 3.12 и устанавливает `backend/requirements.lock`.
`backend/requirements.txt` задаёт прямые зависимости; lock фиксирует их
транзитивное Linux/Python 3.12 окружение.

```bash
cd backend
pytest -q tests/unit tests/tasks
pytest -q tests/integration
ruff check app tests --select E9,F63,F7,F82
```

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

После включения Redis ACL отдельную gated-проверку запускайте внутри Compose-сети
под identity проверяемого сервиса:

```bash
RUN_REDIS_ACL_TESTS=true pytest -q tests/integration/test_redis_acl.py
```

Проверка подтверждает отказ для default/неверных credentials, доступ к
разрешённым ключам и Pub/Sub channels, отказ за пределами ACL scope и чтение
ответов `PSUBSCRIBE`. Запустите её отдельно для API и worker identity; Flower
дополнительно проверяйте по capture worker events после старта.

Запуск с Compose services:

```bash
docker compose up -d postgres redis
cd backend
DB_HOST=localhost REDIS_HOST=localhost ALLOW_PUBLIC_REGISTRATION=true \
  pytest -q tests/integration
```

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

## Полная CI-цепочка

`.github/workflows/ci.yml` запускает:

1. backend critical lint и unit/tasks;
2. integration с PostgreSQL 15 и Redis 7;
3. frontend test/build;
4. online Docker build backend image.

Workflow не выполняет полный Ruff ruleset, Black check, frontend lint,
dependency audit, migration downgrade, smoke Compose и deployment.
`.pre-commit-config.yaml` локально запускает Ruff `--fix` и Black для backend;
его правила шире CI и могут изменять файлы.

Для обновления lock создай чистое Linux-окружение Python 3.12, установи в него
`requirements.txt`, проверь `python -m pip check` и сохрани `pip freeze` в
`requirements.lock`. После этого запусти unit/tasks и integration tests;
изменения lock проходят через обычный CI до merge.

## Что проверять по типу изменения

| Изменение | Минимум |
|---|---|
| Domain rule/service | релевантный unit test + backend critical lint |
| Route/schema/auth | unit + integration endpoint |
| Repository/model/migration | integration на Alembic head |
| Celery task | `tests/tasks` + idempotency/retry scenario |
| Transactional outbox | `tests/unit/services/test_outbox_relay.py`, `tests/integration/test_outbox_api.py`, `tests/integration/test_outbox_relay.py` |
| Frontend API/type/component | Vitest + build |
| Документация | relative links, paths, команды и config keys |

## Ограничения доказательств

Зелёные unit tests не подтверждают tenant isolation всех queries.
Integration suite покрывает основные auth/RBAC/money/resources, но не является
полным API contract test. Docker image build не подтверждает запуск Compose,
миграцию production volume или backup restore.
