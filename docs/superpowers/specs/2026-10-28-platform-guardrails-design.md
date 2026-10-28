# Проект усиления защитных механизмов платформы

## Цель

Усилить текущий односерверный Landlords в четырёх областях: изоляция данных на
уровне PostgreSQL, ограничение частоты запросов, наблюдаемость и надёжность
периодических задач. Цель — добавить независимые от бизнес-кода барьеры и
понятные сигналы для оператора, сохранив текущие FastAPI/PostgreSQL/Redis/Celery,
Caddy и nginx.

## Результаты

- PostgreSQL отклоняет чтение и запись tenant-данных при отсутствии или
  несовпадении контекста аккаунта, даже если прикладной запрос забыл фильтр
  `account_id`.
- Runtime API подключается непривилегированной DB-ролью. Миграции выполняются
  отдельной ролью владельца схемы.
- Аутентифицированные запросы, публичные token-ссылки, регистрации и Celery
  задачи получают явно ограниченный контекст доступа.
- Nginx применяет отдельные лимиты к чувствительным публичным маршрутам, используя
  реальный IP посетителя, переданный только доверенным Caddy.
- Prometheus хранит метрики, Grafana показывает состояние односерверного стека,
  а алерты покрывают недоступность компонентов, ошибки задач и исчерпание диска.
- Beat, worker и outbox-relay имеют проверяемое состояние; пропуски и ошибки
  scheduled-задач становятся видимы.
- Конфигурация и эксплуатационные процедуры документированы; секреты не
  помещаются в репозиторий.

## Вне объёма

- Переход на Kubernetes, multi-host deployment или несколько API/ingress replicas.
- Изменение денежной логики, тарифов и публичного продуктового поведения.
- Перенос документов в S3 или другой внешний storage.
- Публикация Prometheus, Grafana или внутренних метрик в публичный интернет.
- Утверждение, что изменения уже установлены на рабочей VPS: реализация готовит
  конфигурацию; применение к production выполняется отдельно.

## Текущее состояние

- API, migrations, worker, beat и outbox-relay используют общие `DB_USER` /
  `DB_PASSWORD`; defaults Compose — `postgres`.
- Tenant isolation реализована фильтрами в приложении. PostgreSQL RLS не включён.
- Nginx ограничивает несколько точных маршрутов по `$binary_remote_addr`. В
  production Caddy стоит перед nginx, поэтому до лимитирования нужно правильно
  восстановить исходный IP из доверенного proxy-заголовка.
- API предоставляет `/metrics`; ops-код проверяет диск и heartbeat, но в Compose
  нет Prometheus/Grafana/Alertmanager. `/metrics` не проксируется публичным nginx.
- Worker проверяет соединение с Redis, но healthcheck beat и outbox-relay
  отключён. Плановые задачи используют Redis lock; hard time limits задач не
  превышают 600 секунд, а применяемый к ним TTL — 900 секунд.
- Transactional outbox применяется к генерации начислений. Его доставка —
  at-least-once; прочие задачи используют собственные гарантии.

## Рассмотренные подходы

1. **Hardening текущей односерверной схемы — выбрано пользователем.** RLS с
   transaction-local tenant context и отдельной runtime DB-ролью; лимиты в
   nginx после настройки доверенного Caddy proxy; внутренний Prometheus/Grafana/
   Alertmanager с локальными exporters; healthchecks и метрики scheduled-задач.
   Минимизирует новые прикладные зависимости и соответствует текущему topology.
2. **Scale-ready вариант.** Общий Redis rate limiter в приложении и мониторинг,
   рассчитанный на несколько ingress/API replicas. Он лучше делит лимиты между
   репликами, но добавляет middleware, правила доверия proxy и больше runtime
   компонентов, чем требуется текущей VPS.

Выбран первый подход. Ключевой компромисс: nginx limits и scrape targets
рассчитаны на один ingress/API экземпляр; при добавлении реплик лимитирование и
scrape discovery нужно пересмотреть.

## Принятые решения

### RLS в PostgreSQL

- Включить и принудительно применять RLS (`ENABLE` и `FORCE ROW LEVEL SECURITY`)
  ко всем таблицам, содержащим tenant-owned данные. `users` остаётся глобальной
  таблицей идентичности; доступ к `accounts` и таблицам с `account_id` ограничен
  текущим аккаунтом. Список таблиц сверить с моделями и миграциями.
- Политики сравнивают `account_id` (либо `accounts.id`) с transaction-local
  setting `app.account_id`. Отсутствующий контекст даёт deny-by-default. Обычные
  repository-фильтры `account_id` сохраняются как второй слой защиты.
- Разделить DB-права: роль миграций владеет схемой; runtime-роль API/worker не
  является superuser, владельцем tenant-таблиц или `BYPASSRLS`. Runtime получает
  только необходимые DML-права. Локальный и test Compose должны использовать ту
  же модель прав, что и production.
- Для защищённых HTTP-маршрутов tenant ID берётся из проверенного JWT и
  устанавливается до membership/account queries. Активная membership всё равно
  проверяется приложением.
- Публичные invite/invoice/portal routes сохраняют доступ только по capability
  token. До обычного tenant-контекста разрешён узкий token lookup, который
  возвращает только account ID после проверки токена/срока действия; затем
  остальная работа проходит через RLS. Любая `SECURITY DEFINER` функция для
  lookup имеет фиксированный `search_path` и минимальный `EXECUTE` grant.
- Задачи, обрабатывающие один account, получают его ID из проверенного payload и
  устанавливают контекст в своей транзакции. Пакетные задачи обходят аккаунты с
  отдельным контекстом на каждый аккаунт. Outbox relay получает доступ только к
  очереди команд через узкую repository/function boundary; он не получает общий
  `BYPASSRLS`.
- Миграции, demo seed и административные CLI работают с owner/migration URL;
  runtime API не получает эти credentials. Для существующей БД добавить
  повторяемую процедуру provision grants/role до переключения приложения.
- PostgreSQL integration tests запускаются именно runtime-ролью и доказывают:
  tenant A не читает и не меняет tenant B; отсутствие context не открывает
  строки; валидные HTTP, token и task сценарии продолжают работать.

### Ограничение частоты запросов

- Оставить enforcement на публичном ingress в nginx, без новой Redis-зависимости.
- В production доверять forwarded IP только от конкретного Caddy proxy peer и
  применять лимиты к восстановленному client IP. Не принимать клиентский
  `X-Forwarded-For` напрямую.
- Использовать независимые зоны для login/password recovery/registration,
  invite acceptance, публичных claims и reminders. Health, static assets и
  публичный status не ограничивать этими зонами.
- Возвращать HTTP 429 с небольшим JSON error body, совместимым с API error
  envelope. Существующее отключение access log для token-bearing routes
  сохранить.
- Проверить production nginx конфигурацию и proxy цепочку с реальным Caddy
  topology; тестировать, что разные client IP получают независимые лимиты и
  spoofed forwarded header не меняет identity.

### Мониторинг

- Добавить внутренние Compose services Prometheus, Grafana и Alertmanager.
  Prometheus scrape targets остаются в app network. Grafana привязана к
  `127.0.0.1` хоста для доступа через SSH tunnel; внутренние панели и endpoints
  не добавляются в публичный Caddy routing.
- Scrape: API `/metrics`, node exporter, PostgreSQL exporter и Redis exporter.
  Метрики Celery task outcomes и beat heartbeat публикуются без account ID,
  email, URL tokens или других tenant labels.
- Сохранить существующие ops email/Sentry alerts; добавить Prometheus rules для
  недоступности targets, заполнения диска, stale beat/worker, частых task
  failures и terminal outbox failures. Retention и volume должны иметь явный
  односерверный лимит.
- Exporter credentials передаются через secrets/env files, не через labels,
  dashboards или Git. Prometheus/Grafana exporters доступны только внутри
  Compose network, кроме локального Grafana port.

### Планировщик и периодические задачи

- Оставить один Celery beat в Compose; добавить healthcheck процесса beat и
  worker healthcheck, который проверяет ответ worker, а не только доступность
  Redis. Добавить healthcheck для outbox-relay.
- Разделить heartbeat beat-процесса и результаты задач. Для каждой periodic task
  фиксировать last-started, last-success, last-failure и skipped; публиковать
  bounded-cardinality metrics и поднимать stale/failure alerts.
- Сохранить hard time limits; lock TTL должен превышать максимальное время
  задачи с запасом. Не уменьшать TTL; обеспечить проверками, что значения не
  расходятся. При повторной доставке сохранять идемпотентность бизнес-операций.
- Не создавать второй beat и не менять расписание. Восстановление пропущенного
  daily run, где повтор не безопасен, должно быть явно задано для конкретной
  задачи; автоматический catch-up всех пропущенных запусков не добавлять.
- Согласовать документацию: database overview сейчас говорит TTL 600 секунд,
  тогда как текущие задачи передают 900 секунд.

## Порядок внедрения и безопасность

- Изменение RLS должно сначала пройти на изолированной test DB с non-owner
  runtime role; не включать policies на рабочей БД до проверки всех HTTP,
  public-token, CLI и Celery transaction paths.
- Для существующей VPS сначала создать runtime role/grants и секреты, затем
  выполнить schema migration и smoke tests, затем переключить API/worker на
  runtime URL. Owner credentials не удалять до подтверждённого rollback window.
- Monitoring services хранить на VPS с ограниченным retention и не публиковать
  напрямую. Rollback отключает новые scrape/alert services отдельно от данных
  приложения; не удалять monitoring volumes автоматически.
- Не запускать deployment/restart production сервисов в рамках этой работы.

## Критерии готовности

- RLS deny-by-default доказан реальным PostgreSQL runtime role; cross-account
  read/write тесты проходят для HTTP, public links и задач.
- Runtime role не может отключить RLS, читать tenant tables без контекста или
  исполнять миграции.
- Nginx корректно выделяет исходный IP за Caddy, не доверяет spoofed headers,
  возвращает 429 и не пишет capability tokens в access logs.
- Prometheus targets доступны только внутри сети; Grafana доступна только через
  localhost bind; панели и alerts показывают API, host, PostgreSQL, Redis,
  worker, beat, scheduled task outcomes и outbox failures.
- Остановка worker/beat/relay и устойчивый task failure обнаруживаются health
  checks/alerts без tenant-sensitive labels.
- Новые config keys, роли и процедуры обновлены в `.env.example`, configuration,
  deployment, API, database и background-jobs documentation.
- Тестовые fixtures и CI используют изолированную тестовую БД и не подключаются
  к обычному Compose/production database.

## Детали, уточняемые при реализации

- Точный набор RLS-таблиц и узких token lookup entrypoints определяется по всем
  моделям, repository queries и integrations до написания миграции.
- Точный адрес Caddy peer для `set_real_ip_from` должен быть закреплён
  production Compose/network config, чтобы nginx доверял только ingress.
- Метрики Celery выбираются по текущей версии Celery/Prometheus client и должны
  работать с prefork concurrency без общей памяти процесса.
- Alert thresholds задаются консервативно и конфигурируемо; они не должны
  превращать кратковременные рестарты в алерт-шум.
