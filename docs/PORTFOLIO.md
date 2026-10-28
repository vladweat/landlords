# Демонстрация проекта на интервью

Маршрут на 5–10 минут. Цель — показать законченную предметную цепочку и
объяснить решения на конкретных местах в коде, не заявляя о непроверенных
production-свойствах.

## Подготовка

Подними локальный проект по [гайду разработчика](development/getting-started.md),
затем создай демонстрационные данные:

```bash
docker compose exec api python -m app.cli seed-demo
```

Команда создаёт demo user `demo@example.com` с паролем `ChangeMeDemo1!` и
демо-данные. Не используй этот пароль на публичном стенде. Screenshots в
репозитории пока являются SVG-заглушками, см. [assets README](assets/README.md).

## Маршрут

### 1. Проблема и структура приложения — 1 минута

Покажи дашборд и кратко опиши поток: договор → начисления → платежи → баланс и
ROI. Архитектурный обзор: [overview](architecture/overview.md).

### 2. Договор и денежный ledger — 2–3 минуты

Открой договор, покажи начисления и ledger. Объясни, что договор сначала
создаётся как draft, начисления появляются при активации или ручной генерации,
а депозит не смешивается с арендными платежами. Затем покажи частичный платёж,
аванс и распределение FIFO.

Ссылки на правила и сценарии:
[денежный поток](MONEY_FLOW.md),
[use cases](use-cases-contracts-payments.md),
[`payment_service.py`](../backend/app/services/payment_service.py),
[`test_payment_service.py`](../backend/tests/unit/services/test_payment_service.py).

### 3. Изоляция аккаунтов и роли — 1 минута

Покажи раздел команды или объясни три роли и server-side проверку permissions.
В UI скрытые кнопки не являются защитой; права проверяет backend. Смотри
[справку по ролям](multi-user-roles.md),
[`permissions.py`](../backend/app/domain/permissions.py) и
[`test_rbac_api.py`](../backend/tests/integration/test_rbac_api.py).

### 4. Фоновые задачи — 1–2 минуты

Объясни, что транзакционный outbox записывает намерение поставить задачу вместе
с изменением в PostgreSQL, а relay публикует её в Celery после commit. Доставка
может повториться, поэтому обработчики должны быть идемпотентны. Документы:
[фоновые задачи](architecture/background-jobs.md),
[`outbox_relay.py`](../backend/app/services/outbox_relay.py).

### 5. Компромисс и следующий шаг — 1–2 минуты

Выбери один реальный риск из
[реестра техдолга](maintenance/technical-debt.md): например, усилить проверку
Redis command allowlist или подтвердить disaster recovery из offsite-копии.
Уточни, что наличие runbook и restore-check не подтверждает настройку VPS и не
является end-to-end восстановлением приложения.

## Для обсуждения

- Почему роли и tenant scope проверяются backend dependency, а не только UI?
- Какие гарантии даёт transactional outbox и почему он не обеспечивает
  exactly-once delivery?
- Как проверить конкурентную обработку платежей и какой уровень изоляции
  обеспечивает блокировка договора?
- Какие шаги нужны, чтобы перейти от репозиторного backup к проверяемому
  восстановлению после потери VPS?

Источник подробных технических и onboarding материалов —
[индекс документации](index.md).
