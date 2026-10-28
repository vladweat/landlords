# Участие в разработке

## Подготовка

Следуйте [локальному запуску](docs/development/getting-started.md) и
[тестированию](docs/development/testing.md). Перед работой прочитайте
архитектуру затронутого компонента и создавайте небольшое изменение с одной
целью.

## Правила кода

- Backend: Python 3.12, type hints, Black (100 columns), Ruff, русские
  docstrings публичных методов.
- Соблюдать направление `routes → services → repositories → models/domain`.
- Любой доступ к tenant data фильтровать по `account_id`; mutation проверять
  backend permission.
- Денежные расчёты выполнять через `Decimal`, наружу отдавать строки.
- Schema changes — только новой Alembic revision; применённые revisions не
  переписывать.
- Celery tasks проектировать для at-least-once delivery: явные retryable
  exceptions, idempotency, transaction и account context.
- Frontend: доменные типы в `entities`, API/components в `features`, pages
  только компонуют. Server state — TanStack Query.

## Проверка изменения

Минимальный набор выбирайте по таблице в
[testing.md](docs/development/testing.md). Перед review укажите выполненные
команды и то, что не удалось проверить. Не называйте тест успешным, если он не
запускался.

## Документация

Изменение поведения должно обновлять связанный документ в том же change.
Порядок источников истины: код и миграции, runtime-конфигурация и Compose,
CI/tests, затем документация. Не копируйте полные API schemas или список
настроек: ссылайтесь на OpenAPI и на справочник конфигурации.

Технические документы описывают текущее состояние и указывают дату проверки,
если содержат изменчивые эксплуатационные сведения. Планы и закрытые review
чеклисты должны быть явно помечены как исторические. Claims о production,
VPS, внешних провайдерах и восстановлении подтверждайте доступным evidence либо
помечайте как непроверенные. Не добавляйте реальные credentials, URLs с
capability tokens или персональные данные.

Перед review проверьте relative links, пути, команды, env keys и названия
проверок по репозиторию. Основная навигация и правила синхронизации находятся в
[`docs/index.md`](docs/index.md).

## Безопасность данных

Никогда не коммитьте `.env`, dumps, содержимое `storage/documents`, SMTP/Sentry/
YooKassa secrets. Integration tests должны использовать отдельную disposable
database: fixture удаляет и создаёт `landlords_test`.

## Review checklist

- Поведение покрыто тестом, включая error/RBAC/cross-tenant path.
- API envelope и денежные типы согласованы с frontend.
- Migration/rollback и Celery повторное выполнение оценены.
- Config template и документация синхронизированы.
- Diff не содержит generated artifacts и secrets.
