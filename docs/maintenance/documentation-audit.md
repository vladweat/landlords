# Аудит документации

Дата: 28 октября 2026. Область: Markdown-документы репозитория. Сверка
проводилась статически с приложением, миграциями, Compose, CI, конфигурацией,
systemd units, shell scripts и существующими tests. Live VPS и внешние аккаунты
в ходе этого аудита не проверялись; тестовые suite не запускались, так как
изменения документационные.

## Результат

- README стал landing page для интервью и ведёт к отдельной демонстрации и к
  самостоятельному onboarding для нового разработчика.
- API overview приведён к фактическому JSON envelope и исключениям системных
  endpoints, файловых ответов и `204`.
- Архитектура фоновых задач описывает transaction outbox, relay lease/retry и
  возможность повторной доставки.
- Developer setup, конфигурация и testing guide уточнены по Compose, Redis ACL,
  портам и шаблону env.
- Infra/deploy/security согласованы с production Compose overlay, который
  запускает Caddy; backup scripts и restore-check units описаны отдельно от их
  возможной установки на VPS.
- Money flow, roles, use cases и billing отделяют текущее поведение от старого
  backlog и проектных решений.
- `roadmap.md`, `priorities.md`, `backend/todo.md` и `frontend/todo.md` явно
  помечены как исторические документы. Единственный актуальный реестр рисков —
  [technical-debt.md](technical-debt.md).
- В README используются существующие SVG заглушки только с явным пояснением;
  реальные screenshots не создавались.

## Важные исправленные противоречия

1. Base nginx работает по HTTP, но `docker-compose.production.yml` добавляет
   Caddy, который обслуживает домен из `deploy/Caddyfile`; в docs прежнее
   описание требовало внешний TLS ingress и не упоминало overlay.
2. Backup/restore-check scripts и systemd units присутствуют в git. Это не
   доказывает, что units установлены на VPS или что расписание выполняется.
   Restore-check проверяет dump в изолированном PostgreSQL и читаемость архива
   документов, но не запускает приложение и не доказывает disaster recovery.
3. `.env.example` задаёт `SECRET_KEY=change_me`, тогда как production validator
   отклоняет только пустое значение и строку
   `change-me-in-production-change-me`. Поэтому `change_me` принимается. Это
   открытый риск с высоким приоритетом; значение необходимо заменить вручную.
4. API JSON success и application error используют envelope с `data` и
   `message`; у системных endpoints, `204` и файловых ответов отдельные формы.
5. На Redis ACL включён пользовательский режим: диагностические команды должны
   использовать identity `landlords_health`, а не default `redis-cli ping`.

## Что остаётся неподтверждённым

- Доступность домена, DNS, firewall и портов 80/443, активный сертификат Caddy,
  реальный TLS и прямой доступ к origin на VPS.
- Значения production env, конфигурация SMTP/Resend, YooKassa и Sentry, live
  платежи или фактическая отправка писем.
- Установлены ли backup и restore-check systemd units на VPS, когда они
  выполнялись в последний раз, и есть ли копии вне VPS.
- Успешное восстановление всей системы и приложения после потери сервера;
  системный restore-check проверяет только ограниченный сценарий.
- Реальная производительность, нагрузочные характеристики, SLO и RPO/RTO.
- Полнота скриншотов: в репозитории пока только заглушки.

## Правила дальнейшего обновления

Для текущего поведения сначала проверяй source и migrations, затем runtime
configuration/Compose и tests/CI; documentation описывает найденное поведение,
но не заменяет его. При изменении API, модели данных, фоновых задач или
пользовательского поведения обновляй соответствующие справки. Сохраняемый
review или backlog помечай как исторический и не дублируй активный risk
register. Формулируй отдельно то, что есть в repository, что настроено на VPS и
что было реально проверено.
