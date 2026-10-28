# Документация Landlords

Документы описывают реализацию в репозитории, а не состояние production VPS.
Код backend в `backend/app/`, миграции в `backend/alembic/`, frontend в
`frontend/src/`, Compose и CI-конфигурация — источники истины. Live DNS, secrets,
timers и результаты восстановления требуют отдельной проверки окружения.

## Для интервью

- [README проекта](../README.md) — продукт, архитектура и инженерные highlights.
- [Демонстрация за 5–10 минут](PORTFOLIO.md) — showcase flow и вопросы для
  технического обсуждения.
- [Архитектура](architecture/overview.md), [API](api/overview.md),
  [база данных](architecture/database.md),
  [background jobs](architecture/background-jobs.md).
- [Текущие ограничения и техдолг](maintenance/technical-debt.md).

## Для нового разработчика

- [Локальный запуск](development/getting-started.md) — основной onboarding route.
- [Конфигурация](development/configuration.md) и
  [тестирование](development/testing.md).
- [Frontend команды](../frontend/README.md) и
  [правила внесения изменений](../CONTRIBUTING.md).

## Для эксплуатации и security review

| Аудитория | Документ |
|---|---|
| DevOps / on-call | [Деплой](deploy.md), [наблюдаемость](operations/monitoring.md), [устранение сбоев](operations/troubleshooting.md) |
| Security review | [Безопасность](security/overview.md) |
| Coding agent | [`AGENTS.md`](../AGENTS.md) |

## Спецификации и история продукта

- [Денежный поток](MONEY_FLOW.md) и [use cases договоров и платежей](use-cases-contracts-payments.md);
- [роли и multi-tenancy](multi-user-roles.md);
- [оплата Pro через ЮKassa](BILLING.md);
- [архив roadmap](ROADMAP.md) и [архив приоритетов](PRIORITIES.md).

Справки по денежному потоку, договорам, ролям и billing описывают текущие
правила реализации. Roadmap, приоритеты и старые TODO/checklists — история, не
активный backlog. Единственный текущий список инженерных рисков —
[technical-debt.md](maintenance/technical-debt.md). Проверенные расхождения и
границы аудита записаны в
[documentation-audit.md](maintenance/documentation-audit.md).

## Правила поддержки

1. Изменение route, schema или auth dependency сопровождается обновлением
   [API overview](api/overview.md); детальные контракты берутся из OpenAPI.
2. Новая настройка в `backend/app/core/config.py` добавляется в
   [configuration.md](development/configuration.md) и `.env.example`.
3. Миграция или модель, меняющая владение/связи, отражается в
   [database.md](architecture/database.md).
4. Изменение Celery task, расписания, retry или lock обновляет
   [background-jobs.md](architecture/background-jobs.md).
5. Команды документируются только после сверки с CI, package scripts,
   Dockerfile или успешного запуска.
6. Нельзя помещать в документы реальные ключи, пароли и DSN.
7. При изменении пользовательского поведения обновляются product guide и
   соответствующий use case; исторические документы получают дату и пометку,
   что они не являются текущим руководством.
8. Отличай файлы и процедуры, присутствующие в git, от установленных на VPS
   units и проверенных live результатов. Для каждого operational claim укажи
   уровень evidence.
