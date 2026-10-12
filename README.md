# Landlords

SaaS CRM для арендодателей. Реализованы объекты и арендаторы, жизненный цикл
договоров, начисления и платежи с ledger, расходы и ROI, документы и квитанции,
календарь, напоминания, роли аккаунта, портал арендатора и тариф Pro.

Backend — Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 15, Redis 7 и
Celery. Frontend — React 19, TypeScript, Vite, TanStack Query, Zustand и
Tailwind CSS 4. Стек запускается через Docker Compose; nginx обслуживает SPA и
проксирует `/api` в FastAPI.

## Требования и быстрый старт

- Docker с Compose plugin;
- Node.js 22+ и npm — только для frontend с hot reload;
- для offline-сборки backend — корневая `.venv` на Python 3.12; на чистой
  машине используйте `INSTALL_MODE=online`.

```bash
cp .env.example backend/.env
cp .env.example .env
INSTALL_MODE=online docker compose up -d --build
curl -sf http://localhost/ready

# Отдельно frontend с hot reload на http://localhost:3000
cd frontend
npm ci
npm run dev
```

Compose автоматически применяет `docker-compose.override.yml`: API доступен на
`http://localhost:8000`, nginx — на `http://localhost`, PostgreSQL и Redis также
публикуют dev-порты. Не используйте override на публичном сервере.

Публичная регистрация в примере выключена. Демо-аккаунт создаётся идемпотентной
командой:

```bash
docker compose exec api python -m app.cli seed-demo
```

Локальный демонстрационный вход: `demo@example.com` / `ChangeMeDemo1!`. Не
оставляйте этот пароль на публичном стенде.

## Разработка и проверки

```bash
# Все backend-тесты (integration требуют PostgreSQL и Redis)
cd backend
ALLOW_PUBLIC_REGISTRATION=true pytest

# Те же основные группы, что в CI
ruff check app tests --select E9,F63,F7,F82
pytest -q tests/unit tests/tasks
ALLOW_PUBLIC_REGISTRATION=true pytest -q tests/integration

cd ../frontend
npm test
npm run lint
npm run build
```

API применяет `alembic upgrade head` при старте контейнера, потому что только у
сервиса `api` задан `RUN_MIGRATIONS=1`. Ручной запуск из `backend/`:
`alembic upgrade head`.

## Конфигурация

Шаблон находится в [`.env.example`](.env.example). В production обязательны
`APP_ENV=production` и уникальный `SECRET_KEY`; приложение прекращает запуск с
дефолтным ключом. Не коммитьте `.env`, SMTP/Resend, Sentry и ЮKassa credentials.
Полный справочник: [docs/development/configuration.md](docs/development/configuration.md).

## Документация

- [Навигация и статус документов](docs/index.md)
- [Архитектура](docs/architecture/overview.md)
- [API](docs/api/overview.md)
- [База данных](docs/architecture/database.md)
- [Фоновые задачи](docs/architecture/background-jobs.md)
- [Локальная разработка](docs/development/getting-started.md)
- [Тестирование](docs/development/testing.md)
- [Деплой и восстановление](docs/deploy.md)
- [Безопасность](docs/security/overview.md)
- [Технический долг](docs/maintenance/technical-debt.md)

Продуктовые документы (`ROADMAP`, `MONEY_FLOW`, роли и billing) сохранены как
спецификации и исторический контекст. Их статус указан в
[аудите документации](docs/maintenance/documentation-audit.md).

## Известные ограничения запуска

- Compose не настраивает TLS; для публичного сервера нужен внешний TLS
  termination.
- `requirements.txt` не фиксирует большинство версий, поэтому online-сборка не
  полностью воспроизводима.
- `/metrics` не проксируется отдельным location nginx и доступен напрямую через
  dev-порт API либо из внутренней сети.
- Репозиторий содержит процедуры backup/restore, но не их автоматизацию и не
  доказательство тестового восстановления.
