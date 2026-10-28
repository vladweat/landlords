# База данных и транзакции

## Стек и миграции

Используются PostgreSQL 15, SQLAlchemy 2 в синхронном режиме, psycopg2 и
Alembic. Engine и `SessionLocal` создаются в `backend/app/db/session.py`.
`DATABASE_URL` собирается из `DB_*` в `app/core/config.py`.

Схему определяют миграции `backend/alembic/versions/`; ORM-модели не заменяют
миграции. Применение:

```bash
cd backend
alembic current
alembic upgrade head
```

В Compose миграции выполняет `backend/docker-entrypoint.sh` только для `api`
при `RUN_MIGRATIONS=1`. Автоматического rollback schema нет: downgrade следует
проверять отдельно, а восстановление данных выполнять по
[deploy.md](../deploy.md).

## Владение данными

`accounts` — tenant boundary. Большинство бизнес-таблиц содержат `account_id`;
repositories должны включать его в read/update/delete queries. JWT содержит
`account_id`, но dependency дополнительно проверяет активную
`account_memberships`. Это application-level изоляция: PostgreSQL Row Level
Security не настроен.

```mermaid
erDiagram
  users ||--o| account_memberships : belongs
  users ||--o{ auth_sessions : authenticates
  accounts ||--o{ auth_sessions : scopes
  accounts ||--o{ account_memberships : contains
  accounts ||--o{ properties : owns
  accounts ||--o{ tenants : owns
  properties ||--o{ contracts : hosts
  tenants ||--o{ contracts : signs
  contracts ||--o{ rent_charges : schedules
  contracts ||--o{ payments : receives
  rent_charges ||--o{ payments : allocates
  contracts ||--o{ documents : attaches
  properties ||--o{ documents : attaches
  properties ||--o{ property_expenses : incurs
  contracts ||--o{ contract_events : records
  rent_charges ||--o| invoices : exposes
  contracts ||--o{ payment_claims : receives
```

## Основные таблицы

| Группа | Таблицы | Назначение |
|---|---|---|
| Identity | `users`, `accounts`, `account_memberships`, `account_invites`, `auth_sessions` | User, tenant account, роль, приглашения, одноразовый reset-token ID, отзываемые JWT-сессии |
| Rental | `properties`, `tenants`, `contracts`, `contract_templates` | Объекты, арендаторы и договоры; portal token хранится с двухчасовым сроком действия |
| Money | `rent_charges`, `payments`, `property_expenses`, `invoices`, `payment_claims` | Начисления, касса, расходы, публичные квитанции/claims |
| Documents | `documents` | Метаданные файлов; содержимое хранится на диске |
| Operations | `reminders`, `email_dispatch_log`, `notification_dismissals`, `task_outbox` | Дедупликация, пользовательские состояния и durable background commands |
| Audit | `contract_events`, `audit_logs`, `feedback` | История и обратная связь |

`account_memberships` имеет unique `(account_id, user_id)` и unique `user_id`,
поэтому текущая схема допускает только один account на user. Внешние ключи
обычно используют `CASCADE`; у contracts → property/tenant и payments →
contract применяется `RESTRICT`, у optional allocation — `SET NULL`.
Точные constraints необходимо проверять в миграциях, а не по аннотациям модели.

## Деньги

ORM/domain используют `Decimal`; API должен сериализовать денежные значения
строками. `rent_charges` создают обязательство, `payments` уменьшают его.
`payments.rent_charge_id` nullable: отсутствие ссылки означает аванс; сервис
распределяет его FIFO. Депозит — поле договора и не входит в ledger. Полные
инварианты: [money-flow.md](../money-flow.md).

## Индексы

Есть single-column indexes на tenant/FK-поля и составные индексы:

- contracts: `(property_id, status)`, `(account_id, status)`;
- rent charges: `(contract_id, status)`, `(due_date, status)`,
  `(account_id, status)`; unique period identity
  `(account_id, contract_id, period_start, period_end)`;
- payments: `(contract_id, date_paid)`;
- expenses: `(property_id, date_incurred)`.
- auth sessions: primary key `id` для проверки активной сессии, индекс `expires_at` для очистки.

Наличие индекса подтверждено моделями и миграциями, но планы запросов и
production cardinality в репозитории не зафиксированы.

## Транзакции и конкурентность

- HTTP: `get_db_session` commit/rollback на весь request.
- Celery: task создаёт `SessionLocal` и явно commit/rollback.
- Charge-generation outbox row записывается с request mutation; relay делает
  bounded leased claims, но публикует в Redis после commit claim. Начисления и
  outbox completion marker фиксируются одной task transaction.
- Bulk scheduled tasks используют Redis locks с TTL 600 секунд.
- Генерация начислений защищена unique constraint
  `(account_id, contract_id, period_start, period_end)` и PostgreSQL
  `ON CONFLICT DO NOTHING`. Миграция проверяет существующие дубли и отказывает
  в upgrade без удаления финансовых строк.
- Платежные операции берут блокировки в порядке: договор, начисления по due
  date, платежи аванса по дате/созданию. Это сериализует платежные mutations и
  аллокацию авансов внутри договора.
- SaaS renewal фиксирует период, время первой попытки, idempotence key, статус
  и provider payment ID в accounts. Перед новым запросом/восстановлением список
  YooKassa сверяется по metadata периода. Попытка коммитится до HTTP запроса,
  поэтому внешний вызов не удерживает DB transaction/row lock.
- Integration tests создают отдельную `landlords_test`, применяют Alembic head
  и удаляют БД после session.

## Процесс изменения схемы

1. Изменить ORM-модель и создать Alembic revision.
2. Проверить upgrade на копии актуальной схемы и, если применимо, downgrade.
3. Добавить/обновить integration test.
4. Обновить этот документ при изменении ownership, связей или transaction
   assumptions.
5. Не редактировать уже применённые production revisions.
