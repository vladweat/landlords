# Transactional Outbox Design

**Status:** Proposed implementation design, approved in conversation on 2026-10-22.

## Goal

Make HTTP-triggered charge-generation work durable across the PostgreSQL commit and Celery/Redis publication boundary, while tolerating duplicate delivery.

## Current flows in scope

The current code has three producers for `generate_charges_for_contract`:

1. `POST /v1/contracts/generate-charges-bulk` in `backend/app/api/v1/routes/contracts.py`.
2. `POST /v1/contracts/{contract_id}/generate-charges` in the same module.
3. Contract activation with `auto_generate_charges` in `ContractService.update_contract`.

All three must write an outbox row using the same SQLAlchemy session and transaction as the associated request mutation. The API returns the outbox UUID as the Celery task ID so response shape and client polling assumptions remain stable.

## Design

- Add a PostgreSQL outbox model and Alembic migration. A row contains a UUID/task ID, allow-listed task name and payload version, account and contract IDs, timestamps, dispatch lease, delivery attempt count, completion/failure state, and a sanitized last error. Payloads contain identifiers only; credentials and user-provided arbitrary task names are forbidden.
- Insert the outbox row in the business transaction. A rollback must remove both the business change and its queued work.
- Run a separate relay process that polls PostgreSQL in bounded batches using `FOR UPDATE SKIP LOCKED`. It claims rows with an expiring lease, commits the claim, and publishes outside the database transaction. Broker failure releases or expires the lease and schedules bounded exponential retry with jitter. Multiple relay instances may run concurrently.
- Publish to the existing Celery broker using the outbox UUID as `task_id` and include the outbox UUID in task arguments. A successful Redis publish is not completion: the row remains recoverable until the worker commits the business effect and `completed_at` together.
- The task checks outbox state before work. A completed row is a no-op. A successful charge generation and completion marker commit in one PostgreSQL transaction. Worker loss leaves the lease recoverable; a later publication may duplicate the Celery message, so the task and financial writes remain idempotent.
- Record bounded retry and terminal failure state. Retain failed rows for operator inspection and expose pending count, oldest pending age, retry count, and terminal failures through logs/metrics. Do not log payloads or secrets.
- Keep the current account-scoped task inputs and existing unique charge-period constraint. This outbox initially serves only the three producers above; scheduled Celery tasks, email, and billing are out of scope.

## Failure behavior

| Failure point | Required behavior |
|---|---|
| Request transaction rolls back | No outbox row is visible and no task can run. |
| Redis unavailable | Business transaction can commit; relay retains and retries the outbox row. |
| Relay exits after leasing but before publish | Lease expires and another relay retries. |
| Relay exits after publish but before recording publication | Duplicate publish is permitted; worker completion and charge uniqueness prevent duplicate financial effects. |
| Redis loses a published but unprocessed message | Outbox remains incomplete; lease expiry causes a later republication. |
| Worker commits business changes then exits before Celery ACK | Redelivery observes completion and exits without repeating the effect. |
| Permanent task failure | Mark terminal failure, retain evidence, and expose an operational signal; do not silently delete the row. |

## Verification requirements

- PostgreSQL integration tests prove rollback atomicity, successful dispatch/completion, Redis/publisher failure retry, lease recovery, concurrent relay claims, and duplicate delivery idempotency.
- An API integration test proves contract activation and bulk/single enqueue writes share the request transaction and return the stable task ID.
- Run the complete integration suite against the project's dedicated `landlords_test` database. The existing fixture drops and recreates that database; the user has explicitly authorized that test action.
- Test a live relay against the running broker only after deployment; unit mocks do not prove broker availability.

## Constraints

- PostgreSQL remains the durable source of truth; Redis remains a transport and may deliver at least once.
- No cross-resource distributed transaction or exactly-once claim.
- All source edits remain on Windows. The Ubuntu VM has no internet; dependency or image changes must use the existing offline build workflow.
- Schema changes use a new migration; applied migrations are immutable.
- Live service reconfiguration/recreation requires explicit operational authorization.

## Review focus

- A lease must exceed the maximum task execution/retry window or be renewed; otherwise duplicate execution is expected and must stay harmless.
- The task completion marker and financial effects must share one database transaction.
- The relay must never hold row locks while waiting for Redis.
- Queue backlog and terminal failure need visible alerting before production use.
