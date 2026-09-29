# Landlords

CRM для арендодателей: объекты, арендаторы, договоры, начисления и платежи (ledger), расходы, календарь, документы, роли в аккаунте.

Стек: FastAPI + PostgreSQL + Redis/Celery · React (Vite) · Docker Compose.

| Документ | О чём |
|----------|--------|
| [docs/ROADMAP.md](docs/ROADMAP.md) | Стратегия и критерии «готово» |
| [docs/PRIORITIES.md](docs/PRIORITIES.md) | Операционный порядок работ |
| [docs/INFRA.md](docs/INFRA.md) | Инфраструктура и образы |
| [docs/deploy.md](docs/deploy.md) | Runbook: деплой, бэкап, restore |
| [docs/MONEY_FLOW.md](docs/MONEY_FLOW.md) | Денежная логика |

## Быстрый старт (локально)

Нужны Docker Compose и Node 22+ (для dev-фронта).

```bash
# 1. Секреты
cp .env.example backend/.env
# при необходимости: cp .env.example .env  (подстановка DB_* в compose)

# 2. Backend + nginx + Postgres + Redis
docker compose up -d --build

# 3. Frontend (hot reload на :3000, /api → nginx :80)
cd frontend && npm ci && npm run dev
```

API: `http://localhost:8000` (через override) или через nginx `http://localhost/api/…`.  
UI: `http://localhost:3000`.  
Готовность: `curl -sf http://localhost/ready`.

### Демо-аккаунт

```bash
docker compose exec api python -m app.cli seed \
  --email demo@example.com \
  --password 'ChangeMeDemo1!'
```

Создаёт пользователя, аккаунт, один объект и одного арендатора. Пароль только для локальной разработки.

## Прод / VPS

См. [docs/deploy.md](docs/deploy.md). Кратко:

- `APP_ENV=production` и уникальный `SECRET_KEY`
- online-сборка: `INSTALL_MODE=online docker compose -f docker-compose.yml build`
- без `docker-compose.override.yml` (порты БД наружу не открывать)
- один вход: nginx отдаёт SPA и проксирует `/api`

## Разработка

| Часть | Команда |
|-------|---------|
| Frontend | `cd frontend && npm run dev` |
| Backend в Docker | `docker compose up` |
| Тесты | `cd backend && pytest` |
| Миграции | на старте API (`RUN_MIGRATIONS=1`) или `alembic upgrade head` |

Образы API: `INSTALL_MODE=offline` (копирует `.venv`, default) или `online` (`pip install -r requirements.txt`).

### Оплата тарифа Pro (ЮKassa, test)

Подробно: [docs/BILLING.md](docs/BILLING.md). Кратко: в `backend/.env` — `YOOKASSA_SHOP_ID` + `YOOKASSA_SECRET_KEY=test_…`, перезапуск `api`/`celery-*`, Settings → «Оплатить Pro», карта `5555 5555 5555 4444`. После оплаты return → `confirm` без ngrok; webhook опционален.
