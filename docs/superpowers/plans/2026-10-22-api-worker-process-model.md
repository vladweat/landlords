# API Worker Process Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run FastAPI under Gunicorn with Uvicorn workers, graceful process management, a bounded PostgreSQL connection budget, and correct multiprocess Prometheus exposition.

**Architecture:** One Gunicorn master runs in the foreground of each API container. The worker class comes from the separate `uvicorn-worker` package, pinned in the offline dependency bundle. Worker count is explicit and chosen only after database connection and memory budgets are measured; `/metrics` aggregates all worker processes.

**Tech Stack:** Gunicorn 26, Uvicorn, `uvicorn-worker`, Prometheus Python client multiprocess mode, Docker Compose, SQLAlchemy.

**Spec:** [api-worker-process-model.md](../specs/2026-10-22-api-worker-process-model.md)

## Global Constraints

- Use `uvicorn_worker.UvicornWorker`; the old `uvicorn.workers` import path is deprecated.
- VM has no internet; acquire/pin dependency through the local offline artifact path and prove a clean offline image build.
- Keep migrations as a one-time entrypoint action before the Gunicorn master starts.
- Keep total SQLAlchemy connection capacity below PostgreSQL `max_connections` with reserved operational headroom.
- Do not rebuild/recreate live services until the exact operation and impact are approved.

## Review Focus

- Each Gunicorn worker creates its own SQLAlchemy engine pool; multiply pool size and overflow by every API and Celery process.
- Prometheus multiprocess files must be cleaned once at container start, not by each worker.
- Worker exit hooks must mark dead processes and avoid stale metric samples.
- Gunicorn timeout/graceful shutdown must fit observed HTTP request and container stop budgets.
- Offline installation must include all package artifacts and may not call PyPI from Ubuntu.

---

### Task 1: Resolve and package the ASGI worker dependency offline

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/requirements.lock`
- Modify: offline dependency bundle metadata/artifact location already used by the project
- Test: `backend/tests/unit/test_gunicorn_configuration.py`

- [ ] Pin the selected `uvicorn-worker` release exactly and verify its metadata accepts the repository's pinned Uvicorn and Gunicorn versions.
- [ ] Obtain its wheel through the existing local/offline build workflow; do not run `pip install` against PyPI on Ubuntu.
- [ ] Add a failing import/config test for `uvicorn_worker.UvicornWorker`, then verify the package imports in the Linux runtime image.
- [ ] Verify the resolver and clean offline dependency stage using the project's local artifacts.

### Task 2: Configure Gunicorn and process lifecycle

**Files:**
- Create: `backend/gunicorn.conf.py`
- Modify: `backend/Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `backend/docker-entrypoint.sh`
- Modify: `.env.example`, `docs/development/configuration.md`, `docs/deploy.md`
- Test: `backend/tests/unit/test_gunicorn_configuration.py`

**Interfaces:**
- Gunicorn reads `WEB_CONCURRENCY` and explicit timeout/graceful-shutdown settings from environment/config.
- One master binds `0.0.0.0:8000`; Docker remains the container-level supervisor.

- [ ] Test config defaults, invalid worker counts, and migration entrypoint ordering.
- [ ] Implement foreground Gunicorn configuration with `uvicorn_worker.UvicornWorker`, stdout/stderr logs, and graceful shutdown; add worker recycling only if measurements show a concrete need.
- [ ] Ensure Prometheus multiprocess directory is initialized once per API container before importing the app.
- [ ] Verify config check, startup command, Compose config, and migration ordering without starting the live service.

### Task 3: Aggregate API metrics across processes

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/ops_alert_service.py`
- Test: `backend/tests/unit/test_api_metrics.py`

- [ ] Add tests proving `/metrics` aggregates samples from multiple worker metric files and preserves the beat/disk gauges.
- [ ] Implement `CollectorRegistry` with `MultiProcessCollector`, explicit gauge modes, one-time startup cleanup, and Gunicorn child-exit cleanup hook.
- [ ] Verify metrics unit tests and the standard backend critical Ruff check pass.

### Task 4: Budget workers and validate deployment behavior

**Files:**
- Modify: `docs/development/testing.md`
- Modify: `docs/maintenance/technical-debt.md`

- [ ] Read effective PostgreSQL `max_connections`, current API/Celery pool settings, VM memory limits, and representative per-worker RSS without printing credentials.
- [ ] Set initial `WEB_CONCURRENCY` and DB pool values so API, Celery, beat, migration, and monitoring consumers fit below the connection ceiling with reserved headroom.
- [ ] Run representative load checks for latency, RSS, connection count, worker restart, graceful stop, and metric aggregation.
- [ ] Present exact offline build/recreate command and affected API container before applying it; wait for explicit operational approval.
- [ ] After approval, perform the approved offline build/recreation and verify live readiness, worker count/recovery, metrics, and PostgreSQL connection ceiling.
- [ ] Update the technical-debt row only from observed results; do not label the chosen configuration load-tested before the checks pass.
