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

При `DEBUG=false` Swagger/ReDoc отключены, но FastAPI по умолчанию продолжает
публиковать `/openapi.json`; отдельного `openapi_url=None` в коде нет.

## Аутентификация

Login/register/accept invite возвращают JWT HS256 и устанавливают cookie
`access_token`: HttpOnly, `SameSite=Lax`, `Secure` только в production, срок 24
часа. Для API-клиентов поддерживается `Authorization: Bearer <token>`; Bearer
имеет приоритет. Payload содержит `sub`, `account_id`, `exp`.

На каждом protected request `get_current_membership` проверяет активные user и
membership в БД. Role в JWT не хранится. Logout удаляет cookie, но server-side
revocation list отсутствует. Reset token — отдельный JWT на один час.

Публичны auth entrypoints, invite preview/accept, invoice/portal по bearer-like
URL token, status и YooKassa webhook. Остальные routes требуют membership.

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

nginx ограничивает только точные URL login, forgot-password и
`POST /api/v1/reminders` общей zone `10r/m` с burst. В FastAPI rate limiter нет;
обращение напрямую к dev-порту 8000 обходит nginx. TLS в репозитории не
настроен.

## Синхронизация документации

После изменения routes/schemas:

1. запустить приложение с test/dev config;
2. сохранить или сравнить `GET /openapi.json` в CI/artifact при необходимости;
3. проверить frontend API adapters;
4. обновить только группы/особые ограничения в этом документе — не копировать
   все Pydantic schemas вручную.
