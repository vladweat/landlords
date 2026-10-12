# Безопасность

## Trust boundaries

Публичный клиент проходит через nginx к FastAPI; PostgreSQL/Redis в базовом
Compose доступны только сети `app-network`. В dev override их порты и API 8000
публикуются на host. SMTP, YooKassa и Sentry — внешние доверенные сервисы.
Публичные invoice/portal/invite URL содержат capability tokens и должны
обрабатываться как секретные ссылки.

## Authentication

- Пароли хэшируются Passlib bcrypt; bcrypt ограничен 72 bytes и настроен
  `truncate_error=True`.
- Access JWT: HS256, 24 часа, `sub` + `account_id` + `exp`.
- Browser transport: HttpOnly `access_token`, `SameSite=Lax`, `Secure` в
  production. Bearer поддерживается для API/legacy migration.
- Reset JWT действует один час и имеет `type=reset`.
- Logout удаляет cookie только у клиента; denylist/revocation и refresh tokens
  отсутствуют.

Любая компрометация `SECRET_KEY` позволяет подделывать access/reset tokens.
Rotation инвалидирует действующие tokens, но централизованного rotation
runbook нет.

## Authorization и multi-tenancy

Membership и активный user проверяются на каждый protected request; role
загружается из БД. Backend permissions — источник истины. Tenant isolation
реализована repository filters по `account_id`, а не PostgreSQL RLS. Ошибка
фильтра в новом query может раскрыть cross-tenant data, поэтому нужны
integration tests для каждого нового resource.

## HTTP perimeter

nginx добавляет `X-Content-Type-Options`, `X-Frame-Options` и
`Referrer-Policy`, ограничивает body 20 MiB и rate-limit для login,
forgot-password/reminders. HSTS отсутствует, потому что TLS не настроен.
FastAPI импортирует `CORSMiddleware`, но не добавляет его; ожидается same-origin
через nginx/Vite proxy.

CSRF token middleware отсутствует. `SameSite=Lax` снижает риск cross-site
cookie requests, но это не универсальная CSRF-защита при изменении topology,
embedded contexts или unsafe GET. Mutations должны оставаться non-GET; при
cross-site deployment нужна явная CSRF/CORS design.

Rate limiting существует только в nginx и обходится прямым доступом к port
8000. YooKassa webhook не имеет body signature; service повторно читает
состояние через provider API, что описано в `docs/BILLING.md`.

## Secrets и sensitive data

Secrets загружаются из environment/`backend/.env`; secret manager не
интегрирован. `.env` не должен попадать в Git. Логи включают path и query:
tokens нельзя передавать query parameter. Sentry DSN, SMTP, Redis password и
YooKassa key считаются чувствительными.

Documents хранятся на локальном volume, metadata — в PostgreSQL. Download API
для private documents требует membership/account checks; backup должен
защищать и dump, и files. Шифрование at rest репозиторием не настраивается.

## Подтверждённые ограничения

| Severity | Ограничение | Последствие |
|---|---|---|
| High | Нет TLS в repository deployment | Cookie/credentials нельзя безопасно передавать по публичному HTTP |
| Medium | Tenant isolation только application-level | Ошибка repository filter создаёт cross-tenant риск |
| Medium | Нет server-side JWT revocation | Украденный token действует до 24 часов/смены key |
| Medium | Ограниченный nginx rate limit, direct API bypass | Brute-force protection зависит от topology |
| Medium | Нет явной CSRF token защиты | Нужен повторный review при cross-site deployment |
| Low | Swagger скрыт в production, но `/openapi.json` остаётся | Раскрытие API surface |

Это архитектурные риски, не утверждение о факте эксплуатации. Приоритеты и
evidence: [technical-debt.md](../maintenance/technical-debt.md).

## Checklist изменений

- Все reads/writes включают `account_id`.
- Mutation защищена подходящим `Permission`.
- Public token достаточно случайный, не логируется и имеет lifecycle/rotation.
- Error не раскрывает stack, credentials или existence-sensitive details.
- File upload проверяет размер/type/path в service, не только в UI.
- Добавлены negative RBAC и cross-tenant tests.
