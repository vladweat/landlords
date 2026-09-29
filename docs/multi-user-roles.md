# Мультипользовательский аккаунт (роли)

Дизайн и решения по roadmap #6. Реализовано сентябрь 2026; invite по ссылке — сентябрь 2026.

Связанные документы: [ROADMAP.md](./ROADMAP.md), [backend/ARCHITECTURE.md](../backend/ARCHITECTURE.md).

---

## Решения (зафиксировано)

- Роли: **owner / manager / accountant** с матрицей ниже.
- Участников приглашает owner по ссылке (email + full_name + role → письмо / ссылка → accept с паролем). Роли invite: `manager` / `accountant`.
- В v1: один user → одна membership (email уже занят → `ConflictError`).
- Без transfer ownership и без account switcher.
- Источник правды — backend; frontend только скрывает недоступные действия.
- UI и дашборд общие для всех ролей; отличаются права на мутации и блоки «Команда» / «Аккаунт» у owner.

## Матрица прав

| Возможность | owner | manager | accountant |
|---|---|---|---|
| Команда (пригласить/сменить роль/удалить) | да | нет | нет |
| Настройки аккаунта / удаление аккаунта | да | нет | нет |
| Объекты, арендаторы, договоры, документы (CRUD) | да | да | только чтение |
| Платежи, начисления (generate), расходы, reminders | да | да | да |
| Дашборд, календарь, ledger, чтение всего | да | да | да |
| Свой профиль / пароль | да | да | да |

Реализация: enum `Role` + `Permission` + словарь `ROLE_PERMISSIONS` в [`backend/app/domain/permissions.py`](../backend/app/domain/permissions.py). Проверка через dependency `require_permissions(...)` → `ForbiddenError`.

## Модель данных

```mermaid
erDiagram
  users ||--o| account_memberships : has
  accounts ||--o{ account_memberships : has
  accounts ||--|| users : owner_id
  accounts ||--o{ account_invites : invites
  account_memberships {
    uuid id PK
    uuid account_id FK
    uuid user_id FK
    string role
    bool is_active
  }
  account_invites {
    uuid id PK
    uuid account_id FK
    string email
    string role
    string token
    datetime expires_at
    datetime accepted_at
  }
```

- Таблица `account_memberships`: `id`, `account_id`, `user_id`, `role` (`owner|manager|accountant`), `is_active`, timestamps.
- Таблица `account_invites`: pending invite (TTL 7 дней), `token` unique; accept создаёт user + membership.
- Constraints: `UNIQUE(account_id, user_id)`, `UNIQUE(user_id)` (один аккаунт на user в v1).
- `accounts.owner_id` **оставляем** (канонический владелец); при register создаём account + membership `role=owner`.

## Auth / JWT / deps

1. Login / register / accept-invite: account из **membership**, не из `owner_id`.
2. Dependency `get_current_membership`:
   - decode JWT → `user_id`, `account_id`
   - проверить в БД активную membership `(user_id, account_id)`
   - **role всегда из БД** (смена роли owner’ом сразу действует без re-login); в JWT достаточно `sub` + `account_id`
3. `require_permissions(*perms)` поверх membership.
4. `is_active` user и membership — блокируют login и API.

## API

**`GET /v1/auth/me`:**

```json
{
  "status": "success",
  "data": {
    "user": { "...": "..." },
    "account": { "id", "name", "base_currency", "timezone", "owner_id" },
    "role": "owner"
  }
}
```

**Роутер `/v1/account`:**

| Method | Path | Кто | Назначение |
|---|---|---|---|
| GET | `/v1/account` | все роли | настройки аккаунта |
| PATCH | `/v1/account` | owner | `name`, `base_currency`, `timezone` |
| GET | `/v1/account/members` | owner | список участников |
| PATCH | `/v1/account/members/{user_id}` | owner | сменить role (не owner; нельзя сделать второго owner) |
| DELETE | `/v1/account/members/{user_id}` | owner | убрать участника (membership + user) |
| GET | `/v1/account/invites` | owner | список pending-приглашений |
| POST | `/v1/account/invites` | owner | создать invite (`email`, `full_name`, `role` ∈ manager\|accountant) + письмо |
| DELETE | `/v1/account/invites/{id}` | owner | отозвать invite |

**Публично (без JWT):**

| Method | Path | Назначение |
|---|---|---|
| GET | `/v1/public/invites/{token}` | preview (email, role, account name) |
| POST | `/v1/public/invites/{token}/accept` | `{ password, full_name? }` → user + membership + JWT |

**Delete account** (`DELETE /v1/auth/me`): только **owner**; менеджер/бухгалтер → `ForbiddenError`.

**Permissions на routes:**

- properties/tenants/contracts/documents mutate → `WRITE_*`
- payments / generate-charges / expenses / reminders mutate → соответствующие write
- GET — достаточно валидной membership
- feedback — все аутентифицированные

## Слои backend

- Entity / interface / repo: `MembershipEntity`, `AccountInviteEntity`, репозитории
- Service: `AccountService` (list/update/remove members, update account), `InviteService` (create/list/revoke/accept)
- Schemas: `account_schema.py` + invites
- Wire в `deps.py` + `main.py`
- Register / CLI `create-user` / seed — создают membership owner

## Frontend

- Типы: `entities/account.ts` (`Account`, `Role`, `Member`, `Invite`, `Permission`)
- Auth store: `account`, `role` рядом с `user`; обновление из `/me`
- Хелпер `useCan(permission)` в `features/auth/permissions.ts`
- Settings: команда и аккаунт только для owner; invite без пароля; страница `/invite`
- CRUD-страницы: скрыть Create/Edit/Delete без permission
- 403 от API → `showError`

## Тесты

- Unit: `ROLE_PERMISSIONS` / `has_permission`
- Integration (`test_rbac_api.py`, `test_invites_api.py`): register → role; invite → accept → login; accountant 403 на property create; manager 403 на team; remove → login 401; multi-tenancy; expired/revoked

## Вне скоупа v1

- Несколько аккаунтов на одного user / switcher
- Transfer ownership
- Кастомные permissions / биллинг по seats
- Force change password при первом входе
- Отдельный дашборд / навигация под роль
