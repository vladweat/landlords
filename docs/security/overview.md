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
- Access JWT: HS256, 24 часа, `sub` + `account_id` + `jti` + `exp`; каждый JWT
  привязан к записи `auth_sessions` и проверяется по ней на каждом protected request.
- Browser transport: HttpOnly `access_token`, `SameSite=Lax`, `Secure` в
  production и `Cache-Control: no-store`. Auth responses не содержат JWT по
  умолчанию; API-клиент явно включает legacy-compatible Bearer response через
  `X-Return-Bearer-Token: true`.
- Reset JWT действует один час, содержит `jti` и принимается один раз. В БД
  хранится только ID последнего выпущенного reset token; новый запрос сброса
  инвалидирует предыдущую ссылку.
- Logout отзывает конкретную серверную сессию и удаляет cookie. Старые dev-токены
  без `jti` больше не принимаются; после миграции нужно войти заново. Refresh tokens
  не используются. Смена и сброс пароля отзывают все сессии пользователя; для
  продолжения работы нужно войти снова.

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
forgot-password, reset-password и reminders. Compose/nginx не терминирует TLS;
HTTPS redirect и HSTS настраиваются внешним production ingress.
FastAPI импортирует `CORSMiddleware`, но не добавляет его; ожидается same-origin
через nginx/Vite proxy.

Для unsafe methods с cookie-аутентификацией middleware проверяет `Origin` по
`FRONTEND_URL`; отсутствующий и чужой Origin отклоняется. Bearer API-клиенты
не используют cookie и не ограничены этой проверкой. `SameSite=Lax` остаётся
дополнительным уровнем защиты. State-changing operations должны использовать
POST/PUT/PATCH/DELETE: генерация contract PDF переведена с GET на POST.
При изменении frontend/API origins требуется обновить allowlist и повторить
CSRF review.

Rate limiting существует только в nginx и обходится прямым доступом к port
8000. YooKassa webhook не имеет body signature; service повторно читает
состояние через provider API, что описано в `docs/BILLING.md`.

## Secrets и sensitive data

Secrets загружаются из environment/`backend/.env`; secret manager не
интегрирован. `.env` не должен попадать в Git. Application logs не включают
query string и редактируют capability tokens в public API paths; nginx отключает
access log для таких API и frontend token routes. Внешний TLS ingress также
должен исключить token-bearing URL из access logs и analytics. Sentry DSN, SMTP,
Redis password и YooKassa key считаются чувствительными.

Documents хранятся на локальном volume, metadata — в PostgreSQL. Download API
для private documents требует membership/account checks; backup должен
защищать и dump, и files. Шифрование at rest репозиторием не настраивается.

## Подтверждённые ограничения

| Severity | Ограничение | Последствие |
|---|---|---|
| High | Compose/nginx не терминирует TLS | Production требует внешнего HTTPS ingress; прямой публичный HTTP раскрывает credentials |
| Medium | Tenant isolation только application-level | Ошибка repository filter создаёт cross-tenant риск |
| Medium | Нет refresh tokens или интерфейса управления устройствами | Пользователь не может посмотреть/отозвать другие сессии отдельно |
| Medium | Ограниченный nginx rate limit, direct API bypass | Brute-force protection зависит от topology |
| Medium | CSRF защита зависит от FRONTEND_URL и cookie topology | Origin allowlist нужно обновлять при смене public origin; Bearer clients остаются отдельным транспортом |
| Low | Swagger скрыт в production, но `/openapi.json` остаётся | Раскрытие API surface |

Это архитектурные риски, не утверждение о факте эксплуатации. Приоритеты и
evidence: [technical-debt.md](../maintenance/technical-debt.md).

## Checklist изменений

- Все reads/writes включают `account_id`.
- Mutation защищена подходящим `Permission`.
- Public invoice token истекает через 90 дней; tenant portal token — через
  2 часа. Истёкшие ссылки отклоняются и перевыпускаются владельцем.
- Error не раскрывает stack, credentials или existence-sensitive details.
- File upload проверяет размер/type/path в service, не только в UI.
- Добавлены negative RBAC и cross-tenant tests.
