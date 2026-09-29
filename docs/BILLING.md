# SaaS-оплата через ЮKassa

Оплачивается только тариф **Pro** (месяц). **Free** — по умолчанию. **Enterprise** — вручную (`PATCH /account/plan`).

## Что сделать, чтобы заработало

1. Зарегистрируйся в [ЮKassa](https://yookassa.ru/) и создай **демо-магазин** (test).
2. В `backend/.env` заполни:

```env
YOOKASSA_SHOP_ID=<id демо-магазина>
YOOKASSA_SECRET_KEY=test_xxxxxxxx
# опционально:
YOOKASSA_RETURN_URL=http://localhost:3000/settings?billing=return
BILLING_PRO_PRICE_RUB=990
BILLING_GRACE_DAYS=3
```

3. Перезапусти API (и celery, если уже крутится):

```bash
docker compose up -d api celery-worker celery-beat
```

4. Settings → **Оплатить Pro** → тестовая карта без 3DS: `5555 5555 5555 4444` (любой срок/CVC).
5. После оплаты вернёшься на `/settings?billing=return` — фронт вызовет `POST /billing/confirm` и включит Pro **без ngrok**.

### Webhook (желательно для renew / надёжности)

В ЛК демо-магазина → Интеграция → HTTP-уведомления:

`https://<публичный-хост>/api/v1/billing/webhooks/yookassa`

Локально: ngrok/cloudflared на порт 80 (nginx) или 8000 (api).

## Как устроено

| Шаг | Что происходит |
|-----|----------------|
| Checkout | `POST /v1/billing/checkout` → платёж с `save_payment_method=true` → redirect |
| Confirm / webhook | `Payment.find` в API ЮKassa → `plan=pro`, `active`, `period_end=+30д`, сохраняется `payment_method_id` |
| Renew | Celery beat ежедневно: автоплатёж по сохранённому методу |
| Неоплата | `past_due` → через `BILLING_GRACE_DAYS` (3) → Free + write-block на мутации |
| Cancel | Сброс метода оплаты; Free сразу или в конце оплаченного периода |

## Ограничения / что не получится

| Ограничение | Деталь |
|-------------|--------|
| Только Pro | Enterprise не через ЮKassa |
| Нет 54-ФЗ чеков | В платёж не уходит `receipt`; для боевого магазина с онлайн-кассой нужно доработать |
| Автоплатежи в live | В демо доступны сразу; на боевом магазине — согласование с менеджером ЮKassa |
| Webhook без подписи | ЮKassa не подписывает тело; истина всегда из `Payment.find`. IP allowlist в development не режем |
| Без публичного URL | Первая оплата ок через `confirm`. Автопродление идёт через Celery, не через webhook; webhook — запасной канал |
| Цена в коде/env | `BILLING_PRO_PRICE_RUB`; в кабинете ЮKassa отдельных «продуктов» нет |
| Карты с 3DS | Для сохранения метода бери карту **без** 3DS (`5555…4444`), иначе автоплатёж может не сохраниться |
| Offline Docker image | После `pip install yookassa` в `.venv` нужна пересборка образа (`INSTALL_MODE=offline`) |
| Пустые ключи | `billing_enabled=false`, кнопка «Оплатить» недоступна; в `APP_ENV=development` Pro можно выбрать вручную |

## API

- `POST /v1/billing/checkout` — owner
- `POST /v1/billing/confirm` `{ "payment_id" }` — owner, после return
- `POST /v1/billing/cancel` — owner
- `POST /v1/billing/webhooks/yookassa` — без JWT
- `GET /v1/account/subscription` — `subscription_status`, `period_end`, `billing_enabled`, `write_blocked`, цены в каталоге
