# Техническая документация Landlords

Этот раздел описывает фактически реализованную систему. Источники истины:
приложение в `backend/app/`, миграции в `backend/alembic/`, frontend в
`frontend/src/`, Compose и CI-конфигурация. Дата аудита: 12 октября 2026.

## Навигация

| Аудитория | Документ |
|---|---|
| Новый разработчик | [Локальный запуск](development/getting-started.md) |
| Backend/frontend разработчик | [Архитектура](architecture/overview.md), [API](api/overview.md) |
| Разработчик данных | [База данных](architecture/database.md) |
| Разработчик фоновых процессов | [Celery и Redis](architecture/background-jobs.md) |
| DevOps / on-call | [Деплой](deploy.md), [наблюдаемость](operations/monitoring.md), [устранение сбоев](operations/troubleshooting.md) |
| Security review | [Безопасность](security/overview.md) |
| Tech lead | [Технический долг](maintenance/technical-debt.md), [аудит документов](maintenance/documentation-audit.md) |
| Coding agent | [`AGENTS.md`](../AGENTS.md) |

## Спецификации продукта

- [Денежный поток](MONEY_FLOW.md) и [use cases договоров и платежей](use-cases-contracts-payments.md);
- [роли и multi-tenancy](multi-user-roles.md);
- [оплата Pro через ЮKassa](BILLING.md);
- [roadmap](ROADMAP.md) и [приоритеты](PRIORITIES.md).

Эти документы содержат как текущее поведение, так и исторические решения и
backlog. Для эксплуатационных утверждений используйте технические документы
выше; расхождения перечислены в
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
