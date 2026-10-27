# API Worker Process Model Design

**Status:** Proposed implementation design, approved in conversation on 2026-10-22.

## Goal

Run the FastAPI application under a production process manager with graceful worker lifecycle, explicit process count, bounded database connections, and correct Prometheus metrics across processes.

## Design

- Use Gunicorn as the container's foreground master/process manager with the maintained `uvicorn-worker` package class `uvicorn_worker.UvicornWorker`. Do not use the deprecated `uvicorn.workers` import path. Uvicorn recommends Gunicorn for production process management and directs users to the separate worker package: <https://www.uvicorn.org/#running-with-gunicorn>.
- Pin `uvicorn-worker` exactly in the dependency lock and supply it through the offline build artifact path. Its declared compatibility must be verified against the repository's pinned Python 3.12 and Uvicorn version before deployment.
- Put Gunicorn settings in a checked-in config file: bind to `0.0.0.0:8000`, read an explicit `WEB_CONCURRENCY`, use graceful shutdown, staggered max-request recycling, and container-compatible stdout/stderr logs. Do not enable `preload_app` unless startup hooks and per-worker SQLAlchemy pool behavior have been verified.
- Determine `WEB_CONCURRENCY` from measured per-worker memory and a PostgreSQL connection budget, not a CPU-only formula. The budget must include every API worker, Celery worker process, beat/admin clients, migrations, monitoring, and PostgreSQL reserved connections. Current SQLAlchemy defaults are 20 pooled plus 40 overflow connections per process, which are unsafe to multiply without explicit budgeting.
- Configure Prometheus client multiprocess collection before enabling more than one API process. Clean its temporary directory only once at container startup and mark dead workers on exit; `/metrics` must aggregate rather than expose one randomly selected worker's counters.
- Keep one Gunicorn master per API container and let Docker supervise the container. Preserve the existing one-time migration entrypoint before Gunicorn starts workers. Horizontal container scaling is a later deployment change and requires separating migration execution from API replicas first.

## Rollout

1. Add and resolve the worker package using the local/offline artifact process; verify import and `gunicorn --check-config` in the Linux image.
2. Implement and test multiprocess metrics and per-process pool limits.
3. Run a representative load check while observing API latency, process RSS, PostgreSQL connections, and worker restarts. Use this to set the initial `WEB_CONCURRENCY` for the VM.
4. With approval, build and recreate only the API container, then verify health, graceful shutdown, worker recovery, metrics aggregation, and database connection ceilings.

## Acceptance criteria

- Gunicorn master starts the configured number of Uvicorn workers and replaces a failed worker without killing healthy workers.
- Container shutdown lets requests drain within the configured grace period; container restart policy remains the final supervisor.
- Maximum configured SQLAlchemy connections remain below the PostgreSQL connection budget with reserved headroom.
- `/metrics` aggregates counters across workers and does not leak stale multiprocess files across container starts.
- Offline image build succeeds without contacting PyPI, and the exact worker package/runtime versions are documented in the lock.
- Initial worker count is backed by measured memory and connection usage, not asserted as load-tested before the check runs.

## Constraints

- The VM has 4 reported CPUs and 3.8 GiB total memory; this is shared by PostgreSQL, Redis, Celery, Nginx, and API. It does not alone determine a safe worker count.
- The current API image starts one Uvicorn process. This design changes process supervision but does not change API routes or business behavior.
- Service rebuild/recreation and load testing on the live VM require explicit operational approval.
