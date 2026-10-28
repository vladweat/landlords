# Technical Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make developer, API, architecture, data, and security references consistent with the current implementation.

**Architecture:** Keep focused Markdown references and one authoritative home for each contract. Use code, migrations, generated OpenAPI, config and tests to verify claims; link rather than duplicate details.

**Tech Stack:** Markdown, Python/FastAPI/SQLAlchemy/Celery source, TypeScript frontend, Alembic, OpenAPI.

**Spec:** `docs/superpowers/specs/2026-10-28-documentation-overhaul-design.md`

## Global Constraints

- Documentation-only changes; do not edit application code or alter runtime behavior.
- Preserve existing relative links or update every affected link when a page is moved or renamed.
- Keep Russian prose, English identifiers/commands/configuration keys, and the existing Markdown format.
- Do not expose secrets or personal data from local configuration or runtime files.
- Verify Markdown links, command paths, configuration names, and cited symbols against the repository before describing them as current.
- Do not copy large generated OpenAPI schemas into Markdown.

## Review Focus

- Success/error response shapes disagree between route and API documentation — inspect schemas and routes for auth, invites and representative non-auth endpoints.
- Outbox or task delivery guarantees are overstated — compare background-job claims with task/outbox implementation and tests.
- Tenant isolation language implies database enforcement — verify actual repository filters and database policies.
- Security claims disagree across API/security/tech-debt docs — resolve each claim against runtime configuration and its test.
- Example types imply floating-point money or old browser token storage — verify DTO schemas and frontend adapters/types.

---

### Task 1: Reconcile the architecture and data model references

**Files:**
- Modify: `docs/architecture/overview.md`, `docs/architecture/database.md`
- Read: `backend/app/main.py`, `backend/app/api/deps.py`, `backend/app/services/`, `backend/app/db/models/`, `backend/app/db/repositories/`, `backend/alembic/versions/`, `frontend/src/`

- [ ] Verify component boundaries, request/transaction flow, authentication transport, runtime processes, and frontend state ownership against source.
- [ ] Verify entity relationships, uniqueness/foreign-key constraints, account membership rules, money precision, indexes, and outbox/transaction guarantees against migrations and repositories.
- [ ] Correct or qualify every stale architecture/data claim; preserve explicit trade-offs and identify assumptions that source code cannot prove.
- [ ] Keep diagrams at the level maintained by the source; link to exact code paths for details.

### Task 2: Reconcile the API reference

**Files:**
- Modify: `docs/api/overview.md`
- Read: `backend/app/api/v1/routes/`, `backend/app/api/v1/schemas/`, `backend/app/api/responses.py`, `backend/app/main.py`, frontend API adapters, API tests

- [ ] Verify public/protected route groups, auth/cookie/Bearer behavior, response envelopes, validation errors, pagination and rate limits.
- [ ] Remove the stale statement that auth success responses still use top-level fields; document exceptions such as 204 and file responses precisely.
- [ ] Verify all examples match the current Pydantic/OpenAPI schemas, including bearer opt-in and monetary string values.
- [ ] Keep endpoint inventory at group level and direct readers to generated OpenAPI for exact per-route schemas.

### Task 3: Reconcile background jobs and security references

**Files:**
- Modify: `docs/architecture/background-jobs.md`, `docs/security/overview.md`
- Read: `backend/app/tasks/`, `backend/app/services/outbox*`, Celery config, Redis ACL config, `nginx/nginx.conf`, auth/permission middleware, security tests

- [ ] Trace task schedule, delivery, retry, idempotency, outbox, locks, and worker health from implementation; remove the contradictory claim that the outbox is absent.
- [ ] Check authentication, permission, account scoping, capability token lifetimes, CSRF/origin, file constraints, secret handling and exposed docs/metrics against source and tests.
- [ ] Fix OpenAPI exposure claims to match `DEBUG` behavior and `tests/unit/test_openapi_exposure.py`.
- [ ] Label each matrix as an implementation contract or a tested matrix; do not imply exhaustive live security testing.

### Task 4: Reconcile the developer instructions and onboarding references

**Files:**
- Modify: `docs/development/getting-started.md`, `docs/development/testing.md`, `docs/development/configuration.md`, `CONTRIBUTING.md`, `AGENTS.md`, `frontend/README.md`
- Read: `.github/workflows/`, package scripts, `backend/requirements.lock`, Compose files, Dockerfiles, `.env.example`, `backend/app/core/config.py`

- [ ] Verify every command, runtime version, environment key, service port, test prerequisite and CI statement against the referenced source.
- [ ] Remove duplicated procedures or mark one page canonical and link to it.
- [ ] Make frontend README project-specific and remove any remaining template boilerplate.
- [ ] Ensure local/test/production Compose modes and registration configuration are clearly distinguished.
- [ ] Align `CONTRIBUTING.md` and `AGENTS.md` documentation rules with the approved source-of-truth and historical-content policy.

### Task 5: Validate technical references

**Files:**
- Review: all files modified in Tasks 1–4

- [ ] Resolve every relative link in modified pages.
- [ ] Search for contradictory claims about API envelopes, outbox state, OpenAPI exposure, tenant enforcement, and money types.
- [ ] Confirm examples contain no live secrets, local personal data, or unsupported operational claims.
