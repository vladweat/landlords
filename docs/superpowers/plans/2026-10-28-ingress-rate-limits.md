# Ingress Rate Limits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Limit abuse-prone public API routes at nginx using the client IP supplied by the trusted Caddy ingress, while returning the API's JSON error shape.

**Architecture:** Move Caddy into the Compose application network with a fixed address; nginx trusts forwarded client IP only from that address, and Caddy overwrites forwarded IP with its observed peer. Separate nginx zones protect auth, registration, invite acceptance, claims, and reminder creation; all other public routes retain token-safe logging behavior.

**Tech Stack:** Docker Compose, Caddy 2, nginx, shell/curl smoke checks.

**Spec:** `docs/superpowers/specs/2026-10-28-platform-guardrails-design.md`

## Global Constraints

- Enforcement remains at the public ingress in nginx; no new Redis rate-limit dependency.
- Trust forwarded client IP only from the concrete Caddy peer; do not accept client-supplied `X-Forwarded-For` directly.
- Protect login/password recovery/registration, invite acceptance, public claims, and reminders with independent zones.
- Return HTTP 429 with `{"status":"error","message":"Too many requests"}`.
- Preserve access-log suppression for token-bearing public routes.
- Health, readiness, public status, and static assets remain outside these zones.

## Review Focus

- Spoofed `X-Forwarded-For` cannot change the rate-limit identity — verify the Caddy upstream header is overwritten and run a smoke request with a forged value.
- A non-Caddy peer cannot set the client address — verify nginx trusts only Caddy's fixed address.
- Different actual clients receive independent buckets — verify with separate client addresses in the isolated proxy test.
- Token-bearing claim/invite paths remain absent from access logs — verify nginx location precedence and `access_log off`.
- Public 429 responses match the API error envelope — assert exact status, content type, and JSON body.

---

### Task 1: Pin the Caddy-to-nginx proxy identity

**Files:**
- Modify: `docker-compose.yml`, `docker-compose.production.yml`
- Modify: `deploy/Caddyfile`, `nginx/nginx.conf`
- Modify: `docs/development/configuration.md`, `docs/deploy.md`

- [x] Confirm `172.18.0.0/16` does not overlap another configured Docker network on the target test host; use gateway `172.18.0.1` and Caddy address `172.18.0.10` on the Compose network.
- [x] Put Caddy on `app-network`, publish ports 80/443 from Caddy, remove nginx's production host port, and pin Caddy to `172.18.0.10`.
- [x] Keep Caddy's default trusted-proxy behavior (no upstream proxy ranges) so public `X-Forwarded-*` values are ignored; configure nginx real-IP handling to trust only `172.18.0.10` and recursively parse `X-Forwarded-For`.
- [x] Validate both Compose overlays and nginx/Caddy config without restarting the deployed stack.
- [x] Commit the proxy boundary separately.

### Task 2: Apply independent request zones and 429 response

**Files:**
- Modify: `nginx/nginx.conf`
- Test: `deploy/test-rate-limits.sh` (or an equivalent isolated proxy smoke check)

- [x] Preserve auth zone at `10r/m` with burst `5`; add registration and invite-accept zones at `5r/m` burst `2`, public claim zone at `10r/m` burst `3`, and reminder zone at `10r/m` burst `5`.
- [x] Apply limits only to `POST /api/v1/auth/login`, `forgot-password`, `reset-password`, `register`, `POST /api/v1/public/invites/{token}/accept`, invoice/portal `{token}/claim`, and `POST /api/v1/reminders`.
- [x] Set `limit_req_status 429` and a JSON `error` body with the standard envelope.
- [x] Keep token-bearing locations out of access logs while allowing their exact-match/regex locations to reach the intended rate zone.
- [x] Verify independent client buckets, spoofed forwarded-header resistance, exact 429 envelope, and unaffected health/status/static routes in an isolated proxy test.
- [x] Commit request limits separately.

### Task 3: Record ingress operations

**Files:**
- Modify: `docs/api/overview.md`, `docs/deploy.md`, `docs/development/testing.md`

- [x] Document protected route groups, per-minute limits, burst sizes, trusted Caddy address, and the fact that adding ingress replicas requires shared/distributed rate limiting.
- [x] Document safe validation and rollback: inspect Compose/config first, then update nginx/Caddy together so forwarded-IP trust cannot be partially applied.
- [x] Run `git diff --check`, Compose config validation, and nginx/Caddy syntax checks; commit documentation separately.
