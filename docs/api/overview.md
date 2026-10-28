# API

## Адреса и спецификация

FastAPI routes имеют prefix `/v1`; через nginx внешний prefix — `/api/v1`.
Например, frontend вызывает `/api/v1/contracts`, FastAPI получает
`/v1/contracts`. System endpoints `/health`, `/ready`, `/metrics` не
версионированы.

OpenAPI является источником детальных request/response schemas. В development
при `DEBUG=true` доступны:

- `http://localhost:8000/docs`;
- `http://localhost:8000/redoc`;
- `http://localhost:8000/openapi.json`.

При `DEBUG=false` Swagger, ReDoc и `/openapi.json` отключены.

## Аутентификация

Login/register/accept invite устанавливают cookie `access_token`: HttpOnly,
`SameSite=Lax`, `Secure` в production, срок 24 часа, `Cache-Control: no-store`.
По умолчанию JWT не возвращается в JSON. Совместимые API-клиенты, которым нужен
Bearer token, должны явно передавать `X-Return-Bearer-Token: true`; ответ тогда
содержит `token`. Браузерный frontend передаёт `false` и использует cookie.
Для запросов остаётся `Authorization: Bearer <token>`; Bearer имеет приоритет.
Payload access JWT содержит `sub`, `account_id`, `jti`, `exp`. После применения
миграции пользователи с ранее сохранёнными локальными токенами без серверной
сессии должны войти заново; Bearer-клиенты продолжают работать с JWT, выданным
новым login/register/invite flow.

`GET /v1/auth/registration-status` — публичный endpoint без персональных данных;
он возвращает `data.enabled` из `ALLOW_PUBLIC_REGISTRATION`. Login page показывает
ссылку на регистрацию только при `true`; прямой `/register` объясняет, если она
выключена.

На каждом protected request `get_current_membership` проверяет подпись JWT,
активную серверную сессию, user и membership в БД. Role в JWT не хранится.
Logout отзывает сессию; скопированный cookie или Bearer JWT после logout
получает `401`. Смена и сброс пароля отзывают все активные сессии пользователя;
после смены пароля frontend возвращает пользователя на login. Reset token —
отдельный JWT с `type=reset`, действует один час и принимается один раз; новый
запрос сброса инвалидирует предыдущую ссылку. Reset/invite capability помещается
в URL fragment, frontend читает его и удаляет из адресной строки; старые
query-ссылки принимаются для обратной совместимости. Browser session revocation
опирается на `auth_sessions` в PostgreSQL: logout отзывает одну сессию, смена/reset
пароля — все сессии пользователя. Account switching не предоставляется: в v1
пользователь получает одну активную membership при login.

Для unsafe HTTP methods с cookie-аутентификацией backend требует `Origin`,
совпадающий с origin `FRONTEND_URL`; Bearer API-клиенты не зависят от Origin.
`GET /v1/contracts/{id}/document` больше не генерирует данные; генерация PDF
выполняется через `POST`.

Публичны auth entrypoints, invite preview/accept, invoice/portal по bearer-like
URL token, status и YooKassa webhook. Остальные routes требуют membership.
Invoice-ссылка действует 90 дней. `POST /v1/charges/{charge_id}/invoice/rotate-link`
выпускает новый token и сразу инвалидирует предыдущий; маршрут требует
`WRITE_CHARGES`. Публичные invoice data/PDF/claim routes отклоняют expired token.
Публичный PDF GET только читает сохранённый файл; если документ недоступен,
владелец восстанавливает его через `POST /v1/charges/{charge_id}/invoice`.
Ссылка tenant portal действует 2 часа; после истечения владелец может создать
новую ссылку через `POST /v1/contracts/{contract_id}/portal`. Старый токен
отклоняется на публичных data и claim routes. После миграции старые portal
ссылки нужно перевыпустить из договора. Расторжение немедленно отзывает token;
договор со статусом ended/terminated или прошедшей датой окончания не
обслуживается публичным порталом.

## RBAC и tenant isolation

`owner`, `manager`, `accountant` и permissions определены в
`backend/app/domain/permissions.py`. Mutating routes используют
`require_permissions`; subscription write-block применяется к business write
permissions. Repository queries должны фильтровать по `account_id`.

Frontend скрывает запрещённые действия, но не является security boundary.
Матрица: [multi-user-roles.md](../multi-user-roles.md).

## Группы endpoints

Фактические routers подключены в `backend/app/main.py`:

| Prefix | Назначение |
|---|---|
| `/v1/auth`, `/v1/account`, `/v1/billing` | Session, профиль, команда, plan/subscription |
| `/v1/properties`, `/v1/tenants` | Объекты и арендаторы |
| `/v1/contracts`, `/v1/contract-templates` | Договоры, lifecycle, ledger, документы, events, portal |
| `/v1/charges`, `/v1/payments`, `/v1/claims`, `/v1/expenses` | Денежные операции |
| `/v1/calendar`, `/v1/dashboard`, `/v1/notifications`, `/v1/reminders` | Представления и уведомления |
| `/v1/reports`, `/v1/documents`, `/v1/feedback` | Export, файлы, обратная связь |
| `/v1/public/invoices`, `/v1/public/portal`, `/v1/public/invites`, `/v1/public/status` | Token/public flows |

Перечень path/method должен генерироваться из OpenAPI, а не поддерживаться
вручную. Статическая таблица здесь намеренно описывает только группы.

## Форматы, валидация и пагинация

Денежные значения в JSON передаются десятичными строками, чтобы не терять
точность при преобразовании `Decimal`. Это относится и к прогнозу, и к ROI;
проценты доходности и сроки окупаемости остаются числами.

Предпочтительный success envelope:

```json
{"status": "success", "data": {}}
```

Но API пока не полностью унифицирован: некоторые auth endpoints возвращают
`token`/`user` на верхнем уровне, а forgot/reset/change/delete возвращают только
`message`. Клиент должен следовать конкретной OpenAPI schema.

Ожидаемая application error:

```json
{"status": "error", "message": "Описание"}
```

Pydantic error: HTTP 422 с `details`; unexpected error: HTTP 500 с общим
сообщением. nginx rate-limit может вернуть собственный HTML/статус, не envelope.

`PaginationParams`: `page >= 1`, `1 <= per_page <= 100`, defaults 1/20.
Paginated data содержит `items`, `total`, `page`, `per_page`, `pages`; не все
list endpoints обязаны использовать пагинацию. Конкретные filters/sorting
смотрите в query parameters OpenAPI и route-файлах.

Деньги передаются строками. Uploaded body ограничен nginx до 20 MiB; service
может иметь дополнительные file constraints.

## Idempotency и асинхронность

Общего `Idempotency-Key` middleware нет. POST/PATCH следует считать
неидемпотентными, если service явно не гарантирует иное. Billing использует IDs
провайдера, charge generation пытается избегать дублей, но это
endpoint-specific поведение.

Генерация начислений может выполняться Celery асинхронно; успешный enqueue не
означает завершение. Клиент должен перечитать charges/status.

## Rate limiting и transport

nginx ограничивает только точные URL login, forgot/reset-password и
`POST /api/v1/reminders` общей zone `10r/m` с burst. В FastAPI rate limiter нет;
обращение напрямую к dev-порту 8000 обходит nginx. TLS внутри Compose не
настроен: публичный deployment обязан использовать внешний TLS ingress.

## Синхронизация документации

После изменения routes/schemas:

1. запустить приложение с test/dev config;
2. сохранить или сравнить `GET /openapi.json` в CI/artifact при необходимости;
3. проверить frontend API adapters;
4. обновить только группы/особые ограничения в этом документе — не копировать
   все Pydantic schemas вручную.
