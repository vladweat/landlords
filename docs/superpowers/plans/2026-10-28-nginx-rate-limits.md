# План защиты публичных маршрутов rate limiting

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ограничить частые запросы к чувствительным публичным маршрутам по реальному IP клиента за Caddy.

**Architecture:** Enforcement остаётся в nginx. Production nginx доверяет forwarded IP только подтверждённому Caddy peer; лимиты разделены по классам endpoint, ответ на превышение — HTTP 429.

**Tech Stack:** nginx, Docker Compose, Caddy.

**Spec:** `docs/superpowers/specs/2026-10-28-platform-guardrails-design.md`

## Global Constraints

- Не доверять присланному клиентом `X-Forwarded-For` от неизвестного peer.
- Сохранять `access_log off` на token-bearing маршрутах.
- API и базы не публиковать напрямую в production; публичный edge остаётся Caddy → nginx.
- Лимиты должны быть отдельными для auth, public claim/invite и reminders, чтобы один тип запросов не блокировал другие.

## Review Focus

- Nginx видит оригинальный IP за Caddy — проверить на production-overlay test topology.
- Разные IP получают отдельный budget, а spoofed XFF от untrusted peer не меняет ключ лимита.
- Лимит возвращает 429 JSON и не включает token в access logs.
- Регистрация, recovery и публичные claims получают лимиты; health/static/status не затронуты.
- Конфигурация nginx проходит `nginx -t` в собранном image.

---

### Task 1: Зафиксировать и восстановить доверенный client IP

**Files:**
- Modify: `docker-compose.yml`, `docker-compose.production.yml`, `deploy/Caddyfile`, `nginx/nginx.conf`
- Test: `scripts/test-rate-limits.sh` (new) или эквивалентный изолированный proxy smoke test

- [ ] Добавить сценарий smoke test, где запрос от двух client IP через trusted proxy получает разные identity, а прямой запрос со spoofed XFF не может выбрать чужой IP.
- [ ] Запустить сценарий и подтвердить провал на текущей nginx конфигурации.
- [ ] Закрепить trusted proxy peer/network для production Caddy → nginx; не доверять всему внешнему диапазону без обоснования.
- [ ] Настроить nginx real-IP handling только для trusted peer и сохранить передачу нормализованного IP в API.
- [ ] Проверить `docker compose -f docker-compose.yml -f docker-compose.production.yml config` и `nginx -t`.

### Task 2: Добавить раздельные rate zones и API-совместимый 429

**Files:**
- Modify: `nginx/nginx.conf`
- Modify: `docs/api/overview.md`
- Test: `scripts/test-rate-limits.sh`

- [ ] Добавить failing checks для login, forgot/reset password, registration, invite acceptance, public invoice/portal claims и reminders; убедиться, что превышение даёт 429.
- [ ] Разделить зоны по endpoint-классам и задать консервативные rate/burst значения; health, static assets и `/status` не включать.
- [ ] Настроить JSON body `{"status":"error","message":"rate limit exceeded"}` для 429 и документировать его как edge-generated error.
- [ ] Проверить, что routes с capability tokens и invite/reset links по-прежнему не логируются.
- [ ] Запустить rate-limit smoke test с trusted proxy и выполнить `nginx -t`.

### Task 3: CI smoke и эксплуатационная документация

**Files:**
- Modify: `.github/workflows/ci.yml`, `docs/api/overview.md`, `docs/deploy.md`

- [ ] Добавить CI шаг сборки nginx image и `nginx -t`; rate-limit smoke test запускать на изолированном контейнерном topology.
- [ ] Документировать trusted proxy boundary, затронутые endpoints, 429 и способ проверить лимиты без обращения к production данным.
- [ ] Запустить nginx конфигурационный тест и rate-limit smoke test; зафиксировать изменения этого плана отдельным commit.
