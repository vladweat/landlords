# Redis ACL Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace unauthenticated/default-user Redis access with named, scoped Landlords service identities backed by host-only secret files.

**Architecture:** Redis 7 loads a read-only ACL file; `default` is disabled; Compose mounts separate password files for API, Celery, and optional Flower. Application settings read secret files and create authenticated clients. ACL command/key rules are proven against actual Celery, lock, readiness, and ops operations before live activation.

**Tech Stack:** Redis 7 ACL, Docker Compose secrets, Pydantic Settings, redis-py, Celery, pytest.

**Spec:** [redis-acl-hardening.md](../specs/2026-10-22-redis-acl-hardening.md)

## Global Constraints

- Secrets remain outside Git, image layers, command output, and synchronization; do not ask the user to paste a secret into chat.
- Redis remains on the private Compose network with no published host port.
- Production startup requires valid identity and secret-file configuration; development may use isolated unauthenticated Redis.
- The Ubuntu VM has no internet; use the existing Redis 7 image and offline workflow.
- Live service recreation requires explicit approval after presenting the exact operation and its impact.

## Review Focus

- Secret file paths and contents must never be rendered into logs or normal CLI output.
- Redis ACL patterns must cover every Celery broker/result and application lock/ops key, but deny unrelated keys.
- Celery command permissions must be based on actual client behavior, not a guessed command list.
- A failed/missing secret must fail production startup while development/test can still run in isolation.
- Credential rotation must allow old and new credentials to overlap until every client has moved.

---

### Task 1: Secret-file configuration and authenticated Redis URLs

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `.env.example`
- Modify: `backend/tests/unit/test_redis_configuration.py`
- Modify: `docs/development/configuration.md`

**Interfaces:**
- Settings expose `REDIS_USERNAME` and `REDIS_PASSWORD_FILE` and a secret-safe Redis URL builder.
- Existing `REDIS_URL` consumers in readiness, Celery, locks, and ops use the same authenticated URL.

- [ ] Add failing tests for username/password-file URL construction, URL escaping, absent/unreadable files, and production validation.
- [ ] Implement secret-file reading without returning the password in repr/log/error messages; preserve unauthenticated development mode.
- [ ] Verify settings tests and `ruff check app tests --select E9,F63,F7,F82` pass in the backend environment.

### Task 2: Redis ACL and Compose secret wiring

**Files:**
- Modify: `docker-compose.yml`
- Modify: `backend/app/core/config.py`
- Modify: `.env.example`
- Modify: `docs/development/configuration.md`, `docs/deploy.md`, `docs/INFRA.md`
- Test: `backend/tests/unit/test_redis_configuration.py`

- [ ] Add ACL identities for API, worker/beat, and optional Flower; disable the `default` user and limit command categories/key prefixes based on the Redis command/key inventory.
- [ ] Add file-backed Compose secrets sourced only from host paths; mount them read-only and retain Redis on the private network without host-published port 6379.
- [ ] Configure Celery and application key prefixes so ACL patterns are enforceable.
- [ ] Add production checks requiring the appropriate identity and secret file; document host-side secret provisioning and rotation without adding secret files to the repository.
- [ ] Verify `docker compose config --quiet` using temporary non-secret test files and assert rendered output does not reveal secret contents; do not start or rebuild services.

### Task 3: ACL command matrix and live activation

**Files:**
- Test: `backend/tests/integration/test_redis_acl.py`
- Modify: `docs/development/testing.md`
- Modify: `docs/maintenance/technical-debt.md`

- [ ] Add integration checks for unauthenticated rejection, invalid password rejection, default-user disabled, and allowed/denied commands for each identity.
- [ ] Verify API readiness, task publish/consume, result backend, locks, beat, and optional Flower against ACL-enabled Redis.
- [ ] Present exact Compose recreation command, affected containers, outage expectation, and secret-file prerequisites; wait for explicit operational approval.
- [ ] After approval, recreate Redis and dependent clients, run live checks without printing credentials, and record actual results.
- [ ] Update the technical-debt row only after live checks pass; otherwise preserve the unresolved status with the concrete failure.
