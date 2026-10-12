# Локальная разработка

## Вариант 1: весь runtime в Docker

На чистой машине используйте online build:

```bash
cp .env.example backend/.env
cp .env.example .env
INSTALL_MODE=online docker compose up -d --build
docker compose ps
curl -sf http://localhost/ready
```

Автоматически применяется `docker-compose.override.yml`: source backend
монтируется read-only, uvicorn работает с reload, наружу открыты API `8000`,
PostgreSQL `5432` и Redis `6379`. nginx доступен на `80`.

Offline mode — repository-specific оптимизация и требует корневой
`.venv/lib/python3.12/site-packages`:

```bash
INSTALL_MODE=offline docker compose build api celery-worker celery-beat
```

На несовпадающей версии Python этот mode использовать нельзя.

## Frontend с hot reload

```bash
cd frontend
npm ci
npm run dev
```

Vite слушает `0.0.0.0:3000`; `/api` проксируется в nginx на `127.0.0.1:80`.
Production frontend собирается внутри `nginx/Dockerfile`.

## Bootstrap данных

При `ALLOW_PUBLIC_REGISTRATION=false`:

```bash
docker compose exec api python -m app.cli seed-demo
```

Команда создаёт showcase account. Другие доступные команды проверяйте через:

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
`.env` разрешались ожидаемо.

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
- Production-like запуск должен явно исключать override:
  `docker compose -f docker-compose.yml up -d`.

Конфигурация: [configuration.md](configuration.md). Тесты:
[testing.md](testing.md).
