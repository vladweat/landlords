# Transactional Outbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the three HTTP-triggered charge-generation paths durable across PostgreSQL commit and Celery/Redis delivery, with safe at-least-once execution.

**Architecture:** Write one allow-listed charge-generation command to an outbox row in the caller's existing SQLAlchemy transaction. A separate relay process claims rows with expiring leases and publishes stable Celery task IDs; the task completes the outbox row in the same transaction as charge creation so PostgreSQL remains the recovery source if Redis loses a queued message.

**Tech Stack:** FastAPI, SQLAlchemy 2, PostgreSQL, Alembic, Celery, Redis, pytest.

**Spec:** [transactional-outbox.md](../specs/2026-10-22-transactional-outbox.md)

## Global Constraints

- Backend architecture is routes → services → repositories → models; new resource work adds entity/interface, repository, service, DI, and tests.
- Every account-owned query includes `account_id`; financial writes remain idempotent under duplicate delivery.
- Schema changes use a new Alembic migration; applied migrations are immutable.
- Windows is the source-editing environment; Ubuntu has no internet and uses the existing offline image path.
- The integration fixture drops and recreates only `landlords_test`; the user explicitly authorized this test suite.
- Do not start/recreate services or commit/push without the required explicit operational approval.

## Review Focus

- Request rollback must not leave a runnable outbox row; test rollback of both status mutation and row.
- Relay must release DB locks before publishing and use leases for concurrent relay instances.
- Redis can accept a message and the relay can crash before recording publication; duplicate execution must be safe.
- A task's financial changes and completion marker must commit atomically.
- Expired leases, terminal failures, and retry timing must not silently strand jobs or cause unbounded hot-loop retries.

---

### Task 1: Outbox persistence and transaction-bound enqueue

**Files:**
- Create: `backend/app/domain/entities/outbox_message.py`
- Modify: `backend/app/domain/interfaces.py`
- Create: `backend/app/db/models/outbox_message_model.py`
- Modify: `backend/app/db/models/__init__.py`
- Create: `backend/app/db/repositories/outbox_message_repo.py`
- Create: `backend/app/services/task_outbox_service.py`
- Modify: `backend/app/api/deps.py`
- Create: Alembic migration under `backend/alembic/versions/`
- Test: `backend/tests/unit/services/test_task_outbox_service.py`
- Test: `backend/tests/integration/test_outbox_api.py`

**Interfaces:**
- `TaskOutboxService.enqueue_charge_generation(account_id: UUID, contract_id: UUID) -> UUID`
- `OutboxMessageRepository.create_charge_generation(account_id: UUID, contract_id: UUID) -> UUID`
- Both use the caller's SQLAlchemy `Session`; neither commits independently.

- [ ] Add a failing service test for UUID creation, allow-listed task name/payload, and use of the caller's session.
- [ ] Add a failing integration test proving a rolled-back request mutation also rolls back its outbox row.
- [ ] Implement model, domain entity/interface, repository, service, and DI using existing conventions.
- [ ] Add migration with indexes for dispatchable state/lease expiry and account/task lookup; verify upgrade and downgrade against `landlords_test`.
- [ ] Verify unit and focused integration tests pass.

### Task 2: Outbox relay, leases, and durable recovery

**Files:**
- Create: `backend/app/services/outbox_relay.py`
- Create: `backend/app/outbox_relay.py`
- Modify: `backend/app/core/config.py`
- Modify: `docker-compose.yml`
- Modify: `.env.example`, `docs/development/configuration.md`, `docs/architecture/background-jobs.md`
- Test: `backend/tests/unit/services/test_outbox_relay.py`
- Test: `backend/tests/integration/test_outbox_relay.py`

**Interfaces:**
- `OutboxMessageRepository.claim_due_batch(batch_size: int, lease_seconds: int) -> list[OutboxMessage]`
- `OutboxRelay.dispatch_once() -> DispatchSummary`
- `OutboxRelay.run(stop_event: Event) -> None`

- [ ] Test relay behavior for an unavailable publisher, lease expiry, concurrent claims, and successful publish using a fake publisher.
- [ ] Implement bounded `FOR UPDATE SKIP LOCKED` claims; persist lease before network I/O; publish outside transaction; use outbox UUID as Celery `task_id` and pass it to the task.
- [ ] Implement capped exponential retry with jitter and terminal failure recording; emit backlog/age/failure metrics without logging payloads.
- [ ] Add a foreground relay entry point with graceful signal handling and a Compose service using the existing offline-built image.
- [ ] Verify unit tests and focused PostgreSQL integration tests pass; verify `docker compose config --quiet` without starting/rebuilding services.

### Task 3: Complete outbox atomically with charge generation

**Files:**
- Modify: `backend/app/tasks/charge_tasks.py`
- Modify: `backend/app/db/repositories/outbox_message_repo.py`
- Test: `backend/tests/tasks/test_charge_tasks.py`
- Test: `backend/tests/integration/test_outbox_relay.py`

**Interfaces:**
- `generate_charges_for_contract(account_id: str, contract_id: str, outbox_id: str) -> dict[str, Any]`
- `OutboxMessageRepository.mark_completed(session: Session, outbox_id: UUID) -> None`

- [ ] Test completed-task redelivery is a no-op and a task failure does not commit charge changes or completion.
- [ ] Implement outbox state check and commit `completed_at` in the same session/transaction as charge generation.
- [ ] Record retryable versus terminal task failures without exposing IDs beyond existing safe logs.
- [ ] Verify task tests and PostgreSQL duplicate-delivery integration test pass.

### Task 4: Route every producer through the same transaction

**Files:**
- Modify: `backend/app/api/v1/routes/contracts.py`
- Modify: `backend/app/services/contract_service.py`
- Modify: `backend/app/api/deps.py`
- Test: `backend/tests/integration/test_outbox_api.py`
- Test: `backend/tests/unit/services/test_contract_service.py`

**Interfaces:**
- Bulk and single endpoints enqueue with `TaskOutboxService` and return the UUID as `task_id`.
- `ContractService` receives `TaskOutboxService` bound to the same request `Session` and enqueues on activation with auto-generation enabled.

- [ ] Test bulk and single endpoint responses return persisted outbox UUIDs without calling Celery directly.
- [ ] Test activation state and outbox row commit/rollback together.
- [ ] Replace all three direct `send_task` producers and preserve response schemas and eligibility behavior.
- [ ] Run complete `backend/tests/unit` and `backend/tests/tasks`, then the complete integration suite.

### Task 5: Documentation and ledger evidence

**Files:**
- Modify: `docs/architecture/background-jobs.md`
- Modify: `docs/architecture/database.md`
- Modify: `docs/development/testing.md`

- [ ] Document row lifecycle, relay operations, retry/terminal failure handling, and at-least-once guarantees.
- [ ] Update the ledger only after the integration suite and live relay verification actually pass; distinguish database tests from live broker evidence.
- [ ] Run `git diff --check` and review all changed files for unintended modifications.
