# Технический долг и риски

Дата статического аудита: 20 октября 2026. Severity отражает потенциальное
влияние, а не подтверждённый production incident. «Риск» требует runtime/load
verification; «дефект» непосредственно следует из кода.

| Severity | Компонент | Тип | Evidence | Влияние и рекомендация |
|---|---|---|---|---|
| High | Deployment security | Риск | `nginx/nginx.conf` слушает только 80; base Compose публикует `80:80` | TLS завершает внешний ingress; до public go-live требуется проверить HTTPS redirect, HSTS, приватность origin и redaction URL tokens в ingress logs. |
| High | Multi-tenancy | Риск | `app/api/deps.py:get_current_membership`; tenant filters распределены по `db/repositories/*` | RLS/центрального query scope нет: пропущенный `account_id` способен раскрыть данные. Добавить систематические cross-tenant integration tests и рассмотреть scoped repository/RLS. |
| High | Reproducibility | Подтверждено | `backend/requirements.txt` почти полностью без version pins | Online build со временем получает иной dependency graph и может сломаться/получить уязвимую версию. Ввести lock/constraints и controlled update process. |
| Medium | Readiness | Дефект | `app/main.py:readiness`: `session.close()` вызывается только после успешного `execute` | При ошибке после создания Session connection может не закрыться до GC. Использовать context manager/finally; покрыть failure test. |
| Medium | Transactions/scale | Риск | `db/session.py` commit на request; модели не имеют version columns; locks только у bulk Celery | Конкурентные mutations одного договора могут lost-update/race. Выделить критичные use cases, добавить locking/versioning и concurrency tests. |
| Medium | Task delivery | Риск | `celery_app.py`: late ack; enqueue и PostgreSQL commit не объединены; outbox отсутствует | Возможны повтор/пропуск на crash boundary. Сделать все enqueue use cases идемпотентными; для критичных событий рассмотреть transactional outbox. |
| Medium | Celery retries | Подтверждено | `charge_tasks.update_overdue_charges` и `email_tasks.send_daily_reminder_emails` задают `retry_kwargs`, но не `autoretry_for`/`bind+self.retry` | `retry_kwargs` сами по себе не ретраят exception. Определить transient errors и явную retry policy; бизнес-ошибки не ретраить. |
| Medium | File/email durability | Ограничено dev | `email_service.py:_write_file` пишет `storage/emails`; Compose монтирует documents/status, не emails | File fallback работает только вне production и может теряться с container. Production startup требует provider и TLS; readiness не проверяет доступность удалённого SMTP. |
| Medium | Backup/recovery | Пробел | `docs/deploy.md` содержит ручные команды; automation/CI restore drill отсутствуют | Нельзя подтвердить RPO/RTO и восстанавливаемость. Автоматизировать dump, encryption, off-host copy, retention и периодический restore test. |
| Medium | Observability | Пробел | `/metrics` есть; Compose не содержит Prometheus/Alertmanager/log rotation; beat healthcheck disabled | Incident detection зависит от ручных проверок/Sentry/email. Определить scrape/alerts, retention и owner. |
| Medium | Redis hardening | Подтверждено | Compose запускает стандартный `redis:7` без `requirepass`; `REDIS_PASSWORD` настраивает только application URL | Для production включить server-side auth/TLS или изолированную managed instance; не публиковать port. |
| Medium | API process model | Подтверждено | Docker CMD запускает один uvicorn process; `gunicorn` установлен, но не используется | Один process ограничивает concurrency и создаёт single process failure domain. Нагрузочно проверить и выбрать явную worker/restart strategy. |
| Medium | CSRF/topology | Ограничено topology | Cookie auth на unsafe methods проверяет `Origin` по `FRONTEND_URL`; synchronizer token отсутствует; state-changing contract PDF использует POST | Текущая same-origin схема зависит от Origin allowlist и `SameSite=Lax`. При смене public origin или cross-site frontend/API обновить policy и провести CSRF review; ingress должен сохранять browser origin. |
| Medium | Public token lifecycle | Частично ограничено временем | Invite token имеет expiry/revoke; invoice token истекает через 90 дней; portal token — через 2 часа; оба можно перевыпустить | Любой получатель capability URL может открыть данные до истечения срока. Внешний ingress и analytics должны не сохранять token-bearing URL. |
| Low | API consistency | Подтверждено | `api/responses.py` задаёт envelope, но `routes/auth.py` имеет ответы только с `message` или top-level token/user | Клиентам сложнее иметь единый error/success contract. Унифицировать постепенно с versioned compatibility. |
| Low | OpenAPI exposure | Подтверждено | `main.py` отключает docs/redoc, но не `openapi_url` | Production schema остаётся доступна на `/openapi.json`. Решить осознанно: закрыть либо документировать как public. |
| Low | Module coupling | Подтверждено | `api/deps.py`, `services/contract_service.py`, `routes/contracts.py` агрегируют много domains | Изменения имеют широкий blast radius. Делить по bounded feature при следующем функциональном изменении, без rewrite. |
| Low | Config drift | Подтверждено | `core/config.py:LOG_FORMAT`; явной настройки Loguru sink нет | Переменная создаёт ложное ожидание JSON logs. Реализовать или удалить после проверки deployment logging. |

## Coverage gaps

Integration tests покрывают основные resources, RBAC, invoices/portal и
billing, но по inventory отсутствуют отдельные integration suites для
reminders, feedback, reports/export formats, notifications и полного
password-reset/email delivery. Task tests сосредоточены на charge tasks; beat
schedule, email, billing и ops tasks требуют дополнительных failure/retry tests.

## Устаревший исторический долг

`backend/ARCHITECTURE.md` и `backend/TODO.md` полезны как review history, но
часть пунктов уже исправлена (HttpOnly cookie, полный CI, online image). Для
новой приоритизации использовать эту таблицу и сверять каждый пункт с кодом.

## Приоритет действий

1. До публичного запуска: TLS, secrets, закрытие direct API/DB/Redis ports,
   restore drill.
2. Зафиксировать Python dependencies и подтвердить build reproducibility.
3. Закрыть readiness Session leak и формализовать Celery retry/idempotency.
4. Расширить cross-tenant/RBAC tests и concurrency analysis денежных use cases.
5. Подключить metrics/alerts/log retention; определить SLO/RPO/RTO.
