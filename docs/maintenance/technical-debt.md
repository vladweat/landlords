# Технический долг и риски

Дата статического аудита: 21 октября 2026. Severity отражает потенциальное
влияние, а не подтверждённый production incident. «Риск» требует runtime/load
verification; «дефект» непосредственно следует из кода.

| Severity | Компонент | Тип | Evidence | Влияние и рекомендация |
|---|---|---|---|---|
| High | Deployment security | Риск | `nginx/nginx.conf` слушает только 80; base Compose публикует `80:80` | TLS завершает внешний ingress; до public go-live требуется проверить HTTPS redirect, HSTS, приватность origin и redaction URL tokens в ingress logs. |
| High | Multi-tenancy | Риск | `app/api/deps.py:get_current_membership`; tenant filters распределены по `db/repositories/*` | RLS/центрального query scope нет: пропущенный `account_id` способен раскрыть данные. Добавить систематические cross-tenant integration tests и рассмотреть scoped repository/RLS. |
| High | Reproducibility | Подтверждено | `backend/requirements.txt` почти полностью без version pins | Online build со временем получает иной dependency graph и может сломаться/получить уязвимую версию. Ввести lock/constraints и controlled update process. |
| Medium | Readiness | Закрыто; unit-проверка прошла | `app/main.py:readiness` использует `with SessionLocal()`; `tests/unit/test_readiness.py::test_readiness_closes_session_when_database_probe_fails` проверяет закрытие при ошибке; целевой прогон прошёл | DB session закрывается при ошибке probe. Runtime load/failure поведение production отдельно не проверялось. |
| Medium | Transactions/scale | Частично закрыто | PaymentService блокирует contract → charges → advances; rent charges имеют unique period constraint; PostgreSQL scenarios в `tests/integration/test_financial_concurrency.py` прошли | Locks защищают реализованные service paths; прямые SQL mutations в обход сервисов остаются вне гарантии. |
| Medium | YooKassa reconciliation | Ограничено API retention | Renewal сохраняет start time и ищет платёж по account/period metadata; YooKassa list API ограничен историей 3 года | Если неизвестная попытка старше доступной истории, renewal остаётся `unknown` без нового списания; требуется ручная сверка. При недоступности API повтор также ждёт успешного reconciliation. |
| Medium | Task delivery | Риск | `celery_app.py`: late ack; enqueue и PostgreSQL commit не объединены; outbox отсутствует | Возможны повтор/пропуск на crash boundary. Сделать все enqueue use cases идемпотентными; для критичных событий рассмотреть transactional outbox. |
| Medium | Celery retries | Unit-проверки прошли; worker-level retry не проверялся | `charge_tasks.update_overdue_charges` ограничен `OperationalError`; `email_tasks.send_daily_reminder_emails` включает `TransientEmailDeliveryError` в `autoretry_for`; целевые проверки retry policy, email dedup и lock прошли (`8 passed`) | Политика ограничивает retry временными DB/SMTP сбоями; бизнес-ошибки не включены. Фактические повторные запуски Celery worker и backoff не проверялись интеграционно. |
| Medium | File/email durability | Ограничено dev | `email_service.py:_write_file` пишет `storage/emails`; Compose монтирует documents/status, не emails | File fallback работает только вне production и может теряться с container. Production startup требует provider и TLS; readiness не проверяет доступность удалённого SMTP. |
| Medium | Backup/recovery | Пробел | `docs/deploy.md` содержит ручные команды; automation/CI restore drill отсутствуют | Нельзя подтвердить RPO/RTO и восстанавливаемость. Автоматизировать dump, encryption, off-host copy, retention и периодический restore test. |
| Medium | Observability | Пробел | `/metrics` есть; Compose не содержит Prometheus/Alertmanager/log rotation; beat healthcheck disabled | Incident detection зависит от ручных проверок/Sentry/email. Определить scrape/alerts, retention и owner. |
| Medium | Redis hardening | Частично закрыто; unit и Compose config прошли | Compose конфигурирует server-side `requirepass` при заданном `REDIS_PASSWORD`, передаёт его API/worker/beat; production startup требует пароль; `docker compose config --quiet` и unit-проверки прошли | Живое Redis AUTH не запускалось; TLS и фактическая production topology требуют отдельной проверки. |
| Medium | API process model | Подтверждено | Docker CMD запускает один uvicorn process; `gunicorn` установлен, но не используется | Один process ограничивает concurrency и создаёт single process failure domain. Нагрузочно проверить и выбрать явную worker/restart strategy. |
| Medium | CSRF/topology | Ограничено topology | Cookie auth на unsafe methods проверяет `Origin` по `FRONTEND_URL`; synchronizer token отсутствует; state-changing contract PDF использует POST | Текущая same-origin схема зависит от Origin allowlist и `SameSite=Lax`. При смене public origin или cross-site frontend/API обновить policy и провести CSRF review; ingress должен сохранять browser origin. |
| Medium | Public token lifecycle | Частично ограничено временем | Invite token имеет expiry/revoke; invoice token истекает через 90 дней; portal token — через 2 часа; оба можно перевыпустить | Любой получатель capability URL может открыть данные до истечения срока. Внешний ingress и analytics должны не сохранять token-bearing URL. |
| Low | API consistency | Подтверждено | `api/responses.py` задаёт envelope, но `routes/auth.py` имеет ответы только с `message` или top-level token/user | Клиентам сложнее иметь единый error/success contract. Унифицировать постепенно с versioned compatibility. |
| Low | OpenAPI exposure | Закрыто; unit-проверка прошла | `main.py` отключает docs/redoc/openapi при `DEBUG=false`; `tests/unit/test_openapi_exposure.py` проверяет production-like и debug режимы | Schema недоступна в production-like конфигурации; developer docs остаются доступны при `DEBUG=true`. |
| Low | Module coupling | Подтверждено | `api/deps.py`, `services/contract_service.py`, `routes/contracts.py` агрегируют много domains | Изменения имеют широкий blast radius. Делить по bounded feature при следующем функциональном изменении, без rewrite. |
| Low | Config drift | Закрыто; статическая проверка прошла | `LOG_FORMAT` удалён из `Settings` и `.env.example`; ссылки в config/monitoring docs обновлены; `rg` находит имя только в этой записи реестра | Неиспользуемая настройка больше не обещает JSON формат; логирование остаётся в stdout/stderr с форматом библиотек. |

## Coverage gaps

Integration tests покрывают основные resources, RBAC, invoices/portal и
billing, включая добавленные сценарии финансовой конкурентности. Новый
financial concurrency module проверен на PostgreSQL. По inventory отсутствуют отдельные integration suites для
reminders, feedback, reports/export formats, notifications и полного
password-reset/email delivery. Task tests сосредоточены на charge tasks; beat
schedule, email и ops tasks требуют дополнительных failure/retry tests.

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
