# Портфолио — чеклист перед публикацией

Краткий список перед тем, как открыть репозиторий или показать демо рекрутеру.

## Репозиторий

- [ ] В git нет `backend/.env`, корневого `.env`, ключей ЮKassa/SMTP/Sentry
- [ ] `.env.example` актуален: `ALLOW_PUBLIC_REGISTRATION=false`, комментарии к секретам
- [ ] README: быстрый старт, демо-креды, скриншоты, ссылка на этот чеклист
- [ ] `docs/assets/` содержит актуальные скриншоты (см. ниже)

## Локальная проверка

```bash
cp .env.example backend/.env
# при необходимости: cp .env.example .env
docker compose up -d --build
curl -sf http://localhost/ready
docker compose exec api python -m app.cli seed-demo
```

Демо-вход:

- email: `demo@example.com`
- password: `ChangeMeDemo1!`

Проверить: дашборд с цифрами, договоры (active / overdue / draft), платежи, расходы, Settings → тариф без шума про оплату.

## Скриншоты

После `seed-demo` и входа снять три кадра (desktop, ширина ~1280px) и положить в `docs/assets/`:

| Файл | Экран |
|------|--------|
| `docs/assets/dashboard.png` | Дашборд |
| `docs/assets/contracts.png` | Список договоров или карточка с ledger |
| `docs/assets/settings.png` | Настройки (тариф / команда) |

Имена должны совпадать со ссылками в README.

## Что показать рекрутеру

1. Landing → «Демо-доступ» → `/login` с фиксированными кредами.
2. Дашборд и денежный контур (начисления / платежи / ledger).
3. Роли и multi-tenancy (кратко: изоляция по `account_id`, RBAC).
4. Стек и compose: один вход nginx, Celery для фоновых задач.
5. Runbook: [deploy.md](./deploy.md).

## Не делать на публичном демо

- Не включать `ALLOW_PUBLIC_REGISTRATION=true` без rate-limit и мониторинга.
- Не публиковать прод-`SECRET_KEY` и пароли БД из реального VPS.
- Не обещать live HTTPS URL, пока стек не выложен отдельно.
