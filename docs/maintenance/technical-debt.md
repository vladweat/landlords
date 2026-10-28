# Технический долг и риски

Группировка обновлена 28 октября 2026. Раздел «Закрытые» содержит исправленные
пункты с подтверждением в коде или проверках. Результаты прежних прогонов
перенесены из реестра; повторно выполнены только проверки, прямо перечисленные
в соответствующих строках. Этот файл — единственный актуальный реестр рисков.
В разделе «Остаются в проекте» собраны действующие ограничения, частично
решённые вопросы и непроверенные эксплуатационные сценарии. Уровень показывает
потенциальное влияние, а не подтверждённый production incident.

## Закрытые пункты

| Уровень | Компонент | Что закрыто | Подтверждение |
|---|---|---|---|
| Medium | Аналитические N+1 | Forecast, dashboard и portfolio ROI используют пакетные account-scoped выборки. | `ForecastService`, `DashboardService`, `RoiService`; regression tests фиксируют batch-вызовы; backend integration suite прошёл (`130 passed`, `2 skipped`). Новые overview paths должны сохранять пакетный паттерн. |
| Medium | Readiness: утечка DB session | Сессия закрывается и при ошибке DB probe. | `backend/app/main.py:readiness` использует `with SessionLocal()`; `tests/unit/test_readiness.py::test_readiness_closes_session_when_database_probe_fails` проверяет закрытие при ошибке. Целевой прогон прошёл. Нагрузочная проверка production readiness не выполнялась. |
| Medium | Redis ACL: аутентификация и key/channel scope | Ролевые ACL развернуты и проверены для API, worker и Flower. | Gated integration tests прошли для каждой identity (2 теста); Celery ping — `pong`, API `/ready` — `200`, Flower EventReceiver capture прошёл; свежих ACL ошибок в логах нет. Установленный Kombu добавляет `landlords:` к Pub/Sub patterns. Сужение команд Redis вынесено в открытый риск ниже. |
| Low | OpenAPI exposure | OpenAPI, Swagger и ReDoc выключены при `DEBUG=false`. | `backend/app/main.py` задаёт `openapi_url=None` для production-like режима; `tests/unit/test_openapi_exposure.py` проверяет production-like и debug режимы. |
| Low | Config drift: `LOG_FORMAT` | Удалена неиспользуемая настройка и обновлены ссылки в документации. | `LOG_FORMAT` отсутствует в Settings и `.env.example`; поиск находит имя только в этом реестре. Логи остаются в stdout/stderr с форматом библиотек. |

## Риски, остающиеся в проекте

| Уровень | Компонент | Статус | Подтверждение | Влияние и следующий шаг |
|---|---|---|---|---|
| High | Deployment secrets | Шаблон допускает известный placeholder | `.env.example` задаёт `SECRET_KEY=change_me`, а `backend/app/core/config.py::_validate_production_settings` отклоняет только пустое значение и строку `change-me-in-production-change-me`. | Скопированный `change_me` принимается при `APP_ENV=production`. До использования production выдать случайный ключ вручную; исправить расхождение шаблона и startup validation в отдельной задаче. |
| High | Deployment security | Конфигурация в репозитории есть; live topology не проверена | `docker-compose.production.yml` добавляет Caddy; `deploy/Caddyfile` задаёт HTTPS, redirect и HSTS; nginx origin привязан к `127.0.0.1:8080`. | На целевой VPS проверить DNS, доступность 80/443, сертификат, firewall, прямой доступ к API/DB/Redis и redaction URL tokens в ingress logs. Не считать наличие overlay подтверждением live TLS. |
| High | Multi-tenancy | Частично закрыто | `tests/integration/test_multi_tenacy.py` проверяет foreign IDs и основные API paths для tenants, contracts/ledger, documents, charges/payments/invoices и exports; в реестре зафиксирован полный прогон `124 passed`. | Проверенные API paths scoped, но RLS/центрального query scope на уровне БД нет. Расширять cross-tenant проверки для новых ресурсов; отдельно оценить DB-level isolation. |
| High | Dependency reproducibility | Частично закрыто; clean CI build остаётся контрольной точкой | `backend/requirements.lock` содержит pinned dependencies; CI и `backend/Dockerfile` используют lock. Resolver dry-run, `pip check` и `236` unit/task tests прошли в текущем Linux API-контейнере; чистую установку на VM проверить не удалось из-за отсутствия DNS/PyPI. | Подтвердить сборку backend image в CI и периодически проверять чистую установку из lock. |
| Medium | Transactions/scale | Частично закрыто | PaymentService блокирует contract → charges → advances; rent charges имеют unique period constraint; PostgreSQL scenarios в `tests/integration/test_financial_concurrency.py` прошли. | Locks защищают реализованные service paths; прямые SQL mutations в обход сервисов не входят в гарантию. Новые денежные paths включать в concurrency tests. |
| Medium | YooKassa reconciliation | Ограничено сроком хранения API | Renewal сохраняет start time и ищет платёж по account/period metadata; [списки платежей ЮKassa содержат платежи за последние 3 года](https://yookassa.ru/developers/using-api/lists). | Неизвестная попытка старше доступной истории остаётся `unknown` без нового списания и требует ручной сверки. При недоступности API повтор ждёт успешного reconciliation. |
| Medium | Task delivery | Реализовано; live dispatch не подтверждён | Transactional outbox реализован в `services/task_outbox_service.py`, `services/outbox_relay.py` и миграции `task_outbox`; unit и PostgreSQL integration проверки прошли. Live relay опрашивал PostgreSQL и сообщал `claimed=0`. | В live БД не было eligible outbox rows, поэтому реальную публикацию через Celery не проверили. Проверить в staging безопасной тестовой задачей; не создавать тестовое бизнес-событие в рабочей БД. |
| Medium | Celery retries | Unit-проверки прошли; worker-level retry не подтверждён | `charge_tasks.update_overdue_charges` ограничен `OperationalError`; `email_tasks.send_daily_reminder_emails` включает `TransientEmailDeliveryError` в `autoretry_for`; проверки retry policy, email dedup и lock прошли (`8 passed`). | Интеграционно проверить повторные запуски worker и backoff на временных DB/SMTP ошибках. Бизнес-ошибки в retry не включать без отдельного обоснования. |
| Medium | File/email durability | Ограничено dev | `email_service.py:_write_file` пишет в `storage/emails`; Compose не монтирует этот каталог как постоянное хранилище. | File fallback может потеряться вместе с контейнером и не предназначен для production. Production требует provider и TLS; readiness не проверяет доступность SMTP. |
| Medium | Backup/recovery | Процедуры и локальный restore-check реализованы; состояние VPS/offsite не проверено | `deploy/backup-landlords.sh` создаёт DB dump и архив документов; systemd units задают ежедневный backup и еженедельное восстановление в изолированный PostgreSQL. Restore-check проверяет checksum, таблицы и читаемость файлового архива, но не запускает приложение. | Units должны быть установлены и включены на VPS; фактическое расписание и последний результат не проверялись. Копии локальные, `.env`/Redis secrets не входят; нет offsite-копии, шифрования и доказанного app-level DR. Установить offsite-процесс и зафиксировать RPO/RTO. |
| Medium | Observability | Пробел | `/metrics` реализован; Compose не включает Prometheus/Alertmanager/log rotation; healthcheck Celery beat отключён. | Incident detection зависит от ручных проверок/Sentry/email. Определить scrape, alerts, retention, healthcheck и ответственных. |
| Medium | Redis ACL: command scope | Остаётся широким | Генератор ACL задаёт `+@all -@admin -@dangerous` для worker/Flower и `+@read +@write +@connection -@admin -@dangerous` для API; key/channel selectors ограничивают доступ к данным. | Перейти к проверенному allowlist конкретных команд, если совместимость используемых Redis/Celery путей позволяет; расширять права только по результатам smoke tests. |
| Medium | API process model | Стратегия выбрана; нагрузкой не подтверждена | `backend/Dockerfile` запускает один Uvicorn process на API container; настройки задают `DB_POOL_SIZE=20`, `DB_MAX_OVERFLOW=40`, PostgreSQL `max_connections=100`. | До запуска нескольких replicas проверить memory/connection limits под нагрузкой, уменьшить pool budget на instance и настроить scrape каждой replica. |
| Medium | CSRF/topology | Ограничено same-origin схемой | Cookie auth на unsafe methods проверяет `Origin` по `FRONTEND_URL`; synchronizer token отсутствует; contract PDF использует POST. | При смене public origin или cross-site frontend/API пересмотреть CSRF policy. Ingress должен сохранять browser Origin. |
| Medium | Public token lifecycle | Частично ограничено временем | Invite token имеет expiry/revoke; invoice token истекает через 90 дней; portal token — через 2 часа; их можно перевыпустить. | Получатель capability URL имеет доступ до истечения срока. Не сохранять token-bearing URL во внешнем ingress и analytics; при необходимости сокращать TTL/revoke. |
| Low | Module coupling | Подтверждённое ограничение | `api/deps.py`, `services/contract_service.py`, `routes/contracts.py` агрегируют много domains. | Изменения имеют широкий blast radius. Разделять по bounded feature при следующем функциональном изменении, без rewrite. |
| Medium | Test coverage | Неполное покрытие | Отдельные integration suites отсутствуют для reminders, feedback, reports/export formats, notifications и полного password-reset/email delivery. Task tests сосредоточены на charge tasks. | Добавлять тесты по мере изменения соответствующих путей; для Celery отдельно покрыть beat schedule, email и ops failure/retry scenarios. |

## Исторические документы

`backend/architecture.md` и `backend/todo.md` полезны как review history, но
часть пунктов уже исправлена (HttpOnly cookie, полный CI, online image). Для
новой приоритизации использовать разделы выше и сверять каждый пункт с кодом.

## Приоритет действий

1. До публичного запуска: исправить `SECRET_KEY` placeholder guard и проверить TLS/topology/secrets на целевой VPS; подтвердить восстановление приложения из offsite-копии.
2. Сузить Redis command permissions и усилить cross-tenant проверки, включая оценку DB-level isolation.
3. В staging проверить outbox dispatch и Celery retry/backoff на безопасных сценариях.
4. Подтвердить воспроизводимую backend image build из lock в CI; выполнять нагрузочную проверку pool/process модели до масштабирования.
5. Подключить metrics/alerts/log retention и определить SLO/RPO/RTO и владельцев.
