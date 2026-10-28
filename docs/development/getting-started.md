# Локальная разработка

## Требования

- Docker Engine и Docker Compose plugin — для запуска runtime.
- Python 3.12 — для одноразового Redis ACL provisioner на хосте и optional
  offline build backend.
- Node.js 20.19+ или 22.12+ и npm — для frontend build и Vite dev server.

## Запуск среды в Docker

На чистой машине используйте online build:

```bash
cp .env.example backend/.env
cp .env.example .env
cd backend
python -m app.scripts.provision_redis_acl --output-dir ../secrets/redis
cd ..
INSTALL_MODE=online docker compose up -d --build
docker compose ps
curl -sf http://localhost/ready
```

Команда создаёт игнорируемые Git файлы секретов Redis на хосте и не выводит
пароли. Для неё требуется установленный на хосте Python 3.12; сторонние Python
пакеты не нужны. Запускайте её один раз после копирования `.env.example`. Если
`secrets/redis/` уже существует, не перезаписывайте его.

Автоматически применяется `docker-compose.override.yml`: source backend
монтируется read-only, uvicorn работает с reload, наружу открыты API `8000`,
PostgreSQL `5432` и nginx `80`. Redis доступен сервисам только во внутренней
Compose-сети. Тестовый стек использует отдельные loopback-порты; см.
[`testing.md`](testing.md).

Offline mode — repository-specific оптимизация и требует корневой
`.venv/lib/python3.12/site-packages`:

```bash
INSTALL_MODE=offline docker compose build api celery-worker celery-beat outbox-relay
```

На несовпадающей версии Python этот mode использовать нельзя.

## Frontend с hot reload

```bash
cd frontend
npm ci
npm run dev
# После остановки Vite вернитесь в корень репозитория
cd ..
```

Vite слушает `0.0.0.0:3000`; `/api` проксируется в nginx на `127.0.0.1:80`.
Перед сборкой production nginx image создайте `frontend/dist` командой
`npm run build`; Dockerfile nginx копирует эту готовую статику, не запускает
npm build внутри образа.

## Bootstrap данных

При `ALLOW_PUBLIC_REGISTRATION=false`:

```bash
docker compose exec api python -m app.cli seed-demo
```

Команда создаёт showcase account. Список CLI-команд:

Публичную регистрацию локального приложения можно включить настройкой
`ALLOW_PUBLIC_REGISTRATION=true` в `backend/.env`.

```bash
docker compose exec api python -m app.cli --help
```

## Миграции

API container выполняет upgrade автоматически. Ручная проверка:

```bash
docker compose exec api python -m alembic current
docker compose exec api python -m alembic upgrade head
```

При локальном Python команды выполняются из `backend/`, чтобы `alembic.ini` и
`.env` разрешались ожидаемо. Если PostgreSQL работает в Docker, задайте для
локального процесса `DB_HOST=127.0.0.1`; Compose публикует этот порт только
через dev override. Для integration suite используйте изолированный стек из
[testing.md](testing.md), а не рабочий Compose volume.

## Структура

```text
backend/app/       FastAPI, domain, services, repositories, Celery
backend/alembic/   миграции
backend/tests/     unit, tasks, integration
frontend/src/      React SPA
nginx/             SPA image и reverse proxy
storage/           runtime-файлы, не источник кода
docs/              технические и продуктовые документы
```

## Остановка и сброс

```bash
docker compose down
```

`down` сохраняет named volumes. `docker compose down -v` необратимо удаляет
локальные PostgreSQL/Redis данные; выполняйте только при осознанном сбросе.

## Частые особенности

- `docker compose up --build` без `INSTALL_MODE=online` использует offline mode
  и упадёт, если `.venv` отсутствует.
- Health `/health` проверяет только процесс; `/ready` проверяет PostgreSQL и
  Redis.
- Backend пишет dev email в container path `storage/emails`; этот путь не
  смонтирован отдельным volume в базовом Compose, в отличие от documents/status.
- API docs доступны только при `DEBUG=true`.

Конфигурация: [configuration.md](configuration.md). Тесты:
[testing.md](testing.md).
