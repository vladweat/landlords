# Денежный поток — аудит и backlog

Аудит создания договоров и движения денег (начисления → платежи → ledger → дашборд / ROI).  
Сентябрь 2026.

Связанные документы: [ROADMAP.md](./ROADMAP.md), [backend/TODO.md](../backend/TODO.md), [frontend/TODO.md](../frontend/TODO.md), [use cases договоров и платежей](./use-cases-contracts-payments.md).

Отмечай выполненное: `- [ ]` → `- [x]`.

---

## Как устроено сейчас

### Создание договора

1. UI → `POST /contracts` → всегда **`draft`**.
2. `rent_amount` / `deposit_amount` сохраняются; **начислений нет**.
3. Активация (`draft → active`) + флаг `auto_generate_charges` → Celery `generate_charges_for_contract`.
4. **Депозит** — только поле и PDF, не charge и не payment.

| Событие | Начисления |
|---------|------------|
| Create | Нет |
| Activate + `auto_generate_charges=true` | Да (async) |
| Activate + флаг `false` | Нет (есть API `generate-charges`, UI не вызывает) |
| Включить флаг позже без смены статуса | Не генерирует |

### Денежный поток

```
договор active
    → charges (pending)
        → payment
            ├─ с rent_charge_id → на конкретное начисление
            └─ без id → автораспределение FIFO по due_date;
                         остаток → payment без charge («Аванс»)
        → статус charge (paid / partially_paid / overdue / pending)
        → статус договора (active ↔ overdue)
        → ledger: +charge / −payment, running balance
```

**Ledger** (`outstanding = Σ charges − Σ payments`):
- `> 0` — ещё к получению
- `= 0` — сведено
- `< 0` — аванс (деньги получены вперёд)

Математика ledger по кассе **корректна**. UI таблицы: `LedgerTable.tsx` (колонка «После операции», «аванс»).

**ROI / расходы** — уровень объекта, не ledger договора: доход (платежи за 365д) − расходы объекта.

**Квитанция (invoice)** — view поверх charge: PDF + публичная страница `/i/{token}`. Не создаёт ledger-операций; сумма/статус читаются live из charge и платежей. Реквизиты — `accounts.payment_details`.

**Портал арендатора (`/t/{token}`)** — magic link на договор (`contracts.portal_token`): баланс, история, открытые квитанции, реквизиты. Кнопка «Я оплатил» создаёт `payment_claims` (status `pending`, с суммой) и событие `payment_claim`. Landlord в CRM: **Отклонить** или **Подтвердить платёж** — confirm создаёт payment в ledger (FIFO / по charge) и закрывает claim. То же «Я оплатил» доступно на публичной квитанции `/i/{token}`.

---

## Вердикт

| Область | Статус |
|---------|--------|
| Создание / активация / генерация charges | OK по дизайну |
| Ledger (касса) | OK |
| Аванс → покрытие следующих начислений | OK (allocate FIFO) |
| Статусы charges / дашборд outstanding | OK (остатки − аванс; partial+due → overdue) |
| Депозит в учёте | Нет (только метаданные; вне учёта аренды — явно в UI) |

---

## TODO

### P0 — деньги и статусы

- [x] **Распределять аванс на начисления** — при создании платежа, появлении новых charges (generate / renew) и по запросу: FIFO по `due_date` из unlinked payments (`rent_charge_id=None`) в неоплаченные charges. Либо явная сущность «кредит договора».
  - `backend/app/services/payment_service.py`
  - `backend/app/services/rent_charge_service.py`
  - вызовы после `create_charges_batch` / renew

- [x] **Единый outstanding** — считать остаток как `Σ max(0, charge.amount − paid_for_charge)` и опционально вычитать неаллоцированный аванс. Сейчас дашборд суммирует полную сумму charges со `status != paid` и **игнорирует частичные оплаты**.
  - `backend/app/db/repositories/rent_charge_repo.py` → `get_total_outstanding`
  - сверить с `ledger_service` / карточкой договора

- [x] **`partially_paid` + просрочка** — если остаток > 0 и `due_date < today`, статус должен отражать просрочку (например `overdue` или отдельный статус). Сейчас любая частичная оплата навсегда `partially_paid`.
  - `backend/app/domain/rules.py` → `compute_charge_status`
  - Celery `update_overdue_charges`, reminders, UI

### P1 — платежи и UI

- [x] **PaymentModal**: показывать `partially_paid`; max суммы = **остаток** charge, не полная сумма; после create инвалидировать `contract-ledger` / dashboard.
  - `frontend/src/pages/payments/PaymentModal.tsx`
  - `frontend/src/pages/contracts/ContractDetailPage.tsx` (лейбл «Ожидает» для `partially_paid`)

- [x] **Платёж с явным `rent_charge_id`**: проверить `charge.contract_id == dto.contract_id`; избыток сверх остатка → в аванс (как в auto-distribute), не вешать целиком на один charge.
  - `backend/app/services/payment_service.py`

- [x] **Карточка договора**: отрицательный `outstanding_balance` показывать как аванс (как в `LedgerTable`), не как обычное «ожидает оплаты».
  - `frontend/src/pages/contracts/ContractDetailPage.tsx`

- [x] **Автораспределение API**: сейчас возвращается только **первый** split-платёж при нескольких строках — ответ/toast вводят в заблуждение.
  - `payment_service._auto_distribute`

### P2 — создание договора и расписание

- [x] **Prorate** короткого первого/последнего периода в `generate_charge_schedule` (функция `prorate_charge_amount` уже есть для terminate).
  - `backend/app/domain/rules.py`

- [x] **`due_date` vs `period_start`** — при старте договора mid-month и раннем `payment_day` due может быть раньше начала периода → ложная просрочка сразу после activate.

- [x] **UI: ручная генерация charges** — кнопка на детальной странице / после activate (API `generateCharges` уже есть, UI не вызывает); либо toast/poll после активации, пока Celery не создал строки.

- [x] **Депозит** — вне учёта аренды: поле договора + явная пометка в UI/доках (не charge/payment).

### P3 — края и качество

- [x] Terminate: политика для future charges с уже привязанными платежами (`plan_charges_on_terminate`) — unlink → аванс, charge удалить.
- [x] Ledger: стабильный sort `(date, type_order, created_at)` для нескольких платежей в один день.
- [x] Reminder на ledger-строке: не матчить только по `due_date` при нескольких charges в день.
- [x] ROI: не подставлять молча `rent × 12`, если платежей за год 0 — помечать как прогноз (`income_is_forecast`).
- [x] Create: draft можно создать при active/overdue на объекте; конфликт только при activate/renew.
- [x] Тест `test_activate_generates_charges`: патч пути Celery совпадает с `app.celery_app`.

---

## Ключевые файлы

| Слой | Путь |
|------|------|
| Create / activate | `backend/app/services/contract_service.py` |
| Расписание charges | `backend/app/domain/rules.py` (`generate_charge_schedule`, `compute_charge_status`, `compute_ledger_lines`) |
| Batch charges | `backend/app/services/rent_charge_service.py`, `backend/app/tasks/charge_tasks.py` |
| Платежи | `backend/app/services/payment_service.py` |
| Ledger API | `backend/app/services/ledger_service.py` |
| Outstanding дашборда | `backend/app/db/repositories/rent_charge_repo.py` |
| UI договор | `frontend/src/pages/contracts/ContractDetailPage.tsx`, `LedgerTable.tsx` |
| UI платёж | `frontend/src/pages/payments/PaymentModal.tsx` |
| Create UI | `frontend/src/pages/contracts/ContractModal.tsx` |
