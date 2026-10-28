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
- Вход возвращает одинаковую ошибку для отсутствующего, неактивного пользователя
  и неверного пароля; для неизвестного email выполняется bcrypt-проверка dummy-хэша.
- Access JWT: HS256, 24 часа, `sub` + `account_id` + `jti` + `exp`; каждый JWT
  привязан к записи `auth_sessions` и проверяется по ней на каждом protected request.
- Browser transport: HttpOnly `access_token`, `SameSite=Lax`, `Secure` в
  production и `Cache-Control: no-store`. Успешные auth responses не содержат
  JWT в JSON по умолчанию; API-клиент может запросить Bearer token через
  `X-Return-Bearer-Token: true`.
- Reset JWT действует один час, содержит `jti` и принимается один раз. В БД
  хранится только ID последнего выпущенного reset token; новый запрос сброса
  инвалидирует предыдущую ссылку. Reset и invite ссылки передают capability в
  URL fragment (`#token=...`), который браузер не отправляет серверу; frontend
  читает токен и сразу очищает URL. Старые query-ссылки остаются совместимыми.
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

Текущая модель централизует account context в проверенной membership и явно
передаёт его repositories, включая Celery services; поэтому RLS сейчас удвоит
policy surface. Для RLS пришлось бы задавать и очищать account context в каждой
транзакции, покрыть worker/background и public capability flows и сопровождать
policy для каждой tenant table. Возвращаться к RLS стоит при требовании защиты от
ошибок приложения на уровне БД или заметном росте неучтённых query paths.

### Матрица доступа (сверено с кодом 28 октября 2026)

Protected endpoints требуют действительную серверную JWT-сессию и активную
membership; account ID берётся из неё. Указанные permission нужны для mutations;
чтение ресурсов доступно участникам аккаунта без отдельного permission.
Owner имеет все права, manager — write-доступ к объектам/арендаторам/договорам и
документам, accountant — write-доступ только к платежам/начислениям/расходам и
напоминаниям.

| Endpoint | Authentication | Required permission | Account scoping | Sensitive data |
|---|---|---|---|---|
| `POST /v1/auth/register`, `/login`, `/forgot-password`, `/reset-password` | Public; reset token для смены пароля | — | User/reset-token scoped | Email, credentials, reset capability |
| `GET/PUT /v1/auth/me`, `POST /v1/auth/change-password`, `POST /v1/auth/logout`, `DELETE /v1/auth/me` | Session cookie or Bearer; logout may revoke submitted signed token | Account deletion requires owner membership | Current user and membership; session keyed by user/account | Profile, password, account data |
| `/v1/properties`, `/v1/tenants` | Active membership | `WRITE_PROPERTIES`, `WRITE_TENANTS` on writes | Reads/writes scoped to current account | Addresses, tenant identity/contact data |
| `/v1/contracts`, `/v1/contract-templates` and nested ledger, events, charges, documents, portal, claims | Active membership | `WRITE_CONTRACTS`, `WRITE_CHARGES`, `WRITE_DOCUMENTS`, `WRITE_PAYMENTS` by action | Contract/template fetched with current `account_id`; parent records account-scoped | Lease terms, financial history, files, portal link |
| `/v1/charges`, `/v1/payments`, `/v1/expenses`, `/v1/reminders`, `/v1/claims` | Active membership | `WRITE_CHARGES`, `WRITE_PAYMENTS`, `WRITE_EXPENSES`, `WRITE_REMINDERS` as applicable | Resource and contract/charge parent queries include current `account_id` | Amounts, dates, payment notes and claims |
| `/v1/documents/{id}`, property/contract document lists and uploads | Active membership | `WRITE_DOCUMENTS` for upload/delete; download/list require membership | Document and parent lookups include current `account_id` | Private files and metadata |
| `/v1/reports/export`, dashboard, calendar, notifications | Active membership | No additional read permission | Queries receive current `account_id` | Aggregated account finance and activity |
| `/v1/account`, `/v1/account/export`, `/v1/account/members`, `/v1/account/invites` | Active membership | `MANAGE_ACCOUNT` for settings/export; `MANAGE_TEAM` for members/invites | Account and child membership/invite queries are account-scoped | Account settings, member emails/roles, export archive |
| `/v1/billing/*` | Active membership; webhook endpoint is provider callback | `MANAGE_ACCOUNT` for account mutations | Account ID from current membership; webhook reconciles provider payment state | Subscription and provider payment identifiers |
| `/v1/public/invoices/{token}` and `/pdf`, `/claim` | Public capability token; 90-day expiry; rotation invalidates old token | — | Token resolves one invoice; related records use invoice account | Tenant/landlord names, address, amount, payment details |
| `/v1/public/portal/{token}`, `/claim` | Public capability token; 2-hour expiry; rotation invalidates old token | — | Token resolves one contract; related data uses contract account | Lease balance/history and payment details |
| `/v1/public/invites/{token}`, `/accept` | Public capability token; 7-day expiry, one-use; deletion revokes | — | Invite fixes account and role | Invitee email/name, account and role |
| Celery billing/charge/reminder/email tasks | Trusted scheduler/worker, no end-user JWT | Task-specific service policy | Jobs enumerate work then pass account IDs into account-scoped repositories; global maintenance operations are intentionally cross-account | Account financial state, reminders, provider identifiers |
| `/health`, `/ready`, `/metrics`, `/v1/public/status` | Public | — | Operational, not tenant data | Service health/metrics |

Матрица описывает контракты маршрутов и scoped-service patterns, а не утверждает,
что каждый endpoint прошёл отдельный live PostgreSQL negative test в этом аудите.
Существующие integration tests проверяют два аккаунта для основных entity,
вложенных договорных ресурсов, документов, платежей, exports и RBAC; фактически
запущенные проверки перечислены в отчёте аудита.

## HTTP perimeter

nginx добавляет `X-Content-Type-Options`, `X-Frame-Options` и
`Referrer-Policy`, ограничивает body 20 MiB и rate-limit для login,
forgot-password, reset-password и reminders. Base nginx работает по HTTP;
production Compose overlay добавляет Caddy для HTTPS и HSTS. Live DNS,
сертификат и сетевые правила VPS см. в статусе проверки ниже.
FastAPI импортирует `CORSMiddleware`, но не добавляет его; ожидается same-origin
через nginx/Vite proxy.

Для unsafe methods с cookie-аутентификацией middleware проверяет `Origin` по
`FRONTEND_URL`; отсутствующий и чужой Origin отклоняется. Bearer API-клиенты
не используют cookie и не ограничены этой проверкой. `SameSite=Lax` остаётся
дополнительным уровнем защиты; отдельный CSRF token не используется. При
переходе на cross-site frontend/API нужна явная CSRF/CORS policy.
Threat model: блокируются cross-origin формы и запросы браузера, которым
автоматически приложилась бы cookie; проверки `Origin` хватает в текущей
same-origin topology без credentialed CORS. XSS/компрометация frontend и кража
Bearer-токена находятся вне CSRF-защиты.
State-changing operations должны использовать POST/PUT/PATCH/DELETE: генерация
contract PDF переведена с GET на POST.
При изменении frontend/API origins требуется обновить allowlist и повторить
CSRF review.

Rate limiting существует только в nginx и обходится прямым доступом к port
8000. YooKassa webhook не имеет body signature; service повторно читает
состояние через provider API, что описано в `docs/billing.md`.

## Secrets и sensitive data

Secrets загружаются из environment/`backend/.env`; secret manager не
интегрирован. `.env` не должен попадать в Git. Application logs не включают
query string и редактируют capability tokens в public API paths, включая
обработчики ошибок; nginx отключает
access log для таких API и frontend token routes. Внешний TLS ingress также
должен исключить token-bearing URL из access logs и analytics. Sentry DSN, SMTP,
Redis password и YooKassa key считаются чувствительными.
Sentry error/transaction hooks удаляют query strings, редактируют public capability
paths и удаляют Cookie/Authorization headers; `send_default_pii` выключен.

Documents хранятся на локальном volume, metadata — в PostgreSQL. Download API
для private documents требует membership/account checks; backup должен
защищать и dump, и files. Шифрование at rest репозиторием не настраивается.

Upload принимает файлы до 15 MiB, читает не более `MAX_UPLOAD_BYTES + 1`,
проверяет сигнатуру PDF/JPEG/PNG/WebP и её соответствие MIME type и расширению.
Файл пишется во временный файл и атомарно перемещается в storage до вставки
metadata; ошибка записи/flush удаляет частичный файл. Удаление сначала удаляет
metadata в транзакции и оставляет файл до commit: при rollback строка не ссылается
на удалённый файл. После удаления metadata файл становится orphan и удаляется
reconciliation-командой из backend:

```powershell
cd backend
python -m app.scripts.reconcile_document_storage
python -m app.scripts.reconcile_document_storage --delete-orphans
```

Первая команда только перечисляет файлы без metadata. Вторая удаляет только
обычные файлы внутри `DOCUMENTS_STORAGE_DIR`, отсутствующие в
`documents.file_path`; symlink пропускаются. Failed DB commit при upload может
оставить orphan-файл, который удаляется тем же dry-run-first процессом.
Public invoice PDF GET только читает готовый документ. Если metadata или файл
отсутствует, запрос возвращает 404 без новых записей; владелец может восстановить
квитанцию через `POST /v1/charges/{charge_id}/invoice`.

## Подтверждённые ограничения

| Severity | Ограничение | Последствие |
|---|---|---|
| High | Live TLS topology не подтверждена | Production overlay содержит Caddy, но DNS, firewall, certificate и прямой доступ к origin на VPS не проверены |
| Medium | Tenant isolation только application-level | Ошибка repository filter создаёт cross-tenant риск |
| Medium | Нет refresh tokens или интерфейса управления устройствами | Пользователь не может посмотреть/отозвать другие сессии отдельно |
| Medium | Ограниченный nginx rate limit, direct API bypass | Brute-force protection зависит от topology |
| Medium | CSRF защита зависит от FRONTEND_URL и cookie topology | Origin allowlist нужно обновлять при смене public origin; Bearer clients остаются отдельным транспортом |
Production Compose overlay содержит Caddy для HTTPS и HSTS. Фактические DNS,
сетевые правила VPS и состояние сертификата зависят от настройки окружения.

## Checklist изменений

- Все reads/writes включают `account_id`.
- Mutation защищена подходящим `Permission`.
- Public invoice token истекает через 90 дней; tenant portal token — через
  2 часа. Истёкшие ссылки отклоняются и перевыпускаются владельцем. Portal
  закрывается при terminated/ended договоре и после `end_date`; invoice остаётся
  доступен до expiry/rotation для оплаты уже выставленного начисления.
- Error не раскрывает stack, credentials или existence-sensitive details.
- File upload проверяет размер/type/path в service, не только в UI.
- Добавлены negative RBAC и cross-tenant tests.
