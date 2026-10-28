# Operations and Product Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give operators accurate procedures and give readers concise, current descriptions of product workflows, risks, and historical plans.

**Architecture:** Preserve the existing Markdown corpus, but separate current runbooks and product behavior from planning/review history. Use repository configuration for repeatable steps and label all live-environment claims by evidence level.

**Tech Stack:** Markdown, Docker Compose/systemd/backup scripts, FastAPI/Celery source, tests and existing project plans.

**Spec:** `docs/superpowers/specs/2026-10-28-documentation-overhaul-design.md`

## Global Constraints

- Documentation-only changes; do not edit application code or alter runtime behavior.
- Preserve existing relative links or update every affected link when a page is moved or renamed.
- Keep Russian prose, English identifiers/commands/configuration keys, and the existing Markdown format.
- Do not expose secrets or personal data from local configuration or runtime files.
- Verify Markdown links, command paths, configuration names, and cited symbols against the repository before describing them as current.
- Distinguish repository procedures from configured VPS state and verified live outcomes.

## Review Focus

- A command modifies or deletes production data — compare it to scripts/config and mark prerequisites, scope and irreversible effects.
- A backup description implies offsite safety or an application-level restore drill — separate repository implementation from VPS deployment and recovery evidence.
- An operational procedure assumes an unavailable provider/secret — mark required environment and safe local alternatives.
- A product checklist shows completed work as an open task — classify it as current behavior, future roadmap, or dated history.
- A technical-debt item is now fixed or has never been verified — cross-check recent source/tests and preserve evidence level.

---

### Task 1: Verify configuration, deployment and operations procedures

**Files:**
- Modify: `docs/development/configuration.md`, `docs/deploy.md`, `docs/INFRA.md`, `docs/operations/monitoring.md`, `docs/operations/troubleshooting.md`
- Read: `.env.example`, Compose files, `deploy/`, `nginx/`, Dockerfiles, systemd units, config source, `docs/security/overview.md`

- [ ] Verify each command, file path, env key, service name, port, timer, retention value, and health endpoint against the repository.
- [ ] For backup/recovery, document separately: scripts shipped in the repository, systemd installation/configuration steps, what the restore-check validates, and what remains unproven about offsite disaster recovery and application consistency.
- [ ] Reconcile duplicate deployment/infra/monitoring instructions by choosing a canonical runbook and linking to it.
- [ ] Label external ingress, provider availability, live VPS configuration, and restore drill status as unverified unless current evidence is available.
- [ ] Review shell blocks for destructive commands, unsafe defaults and accidental secret exposure.

### Task 2: Rewrite current product workflow references

**Files:**
- Modify: `docs/MONEY_FLOW.md`, `docs/use-cases-contracts-payments.md`, `docs/BILLING.md`, `docs/multi-user-roles.md`
- Read: relevant routes/services/domain rules, frontend components, schemas and tests

- [ ] Convert the money-flow audit/backlog into a concise current domain guide; remove closed task checklists while retaining ledger, allocation, status and deposit invariants.
- [ ] Verify contract lifecycle and payment scenarios against current service/domain behavior, API schemas and UI; correct only facts that are proven by implementation.
- [ ] Update billing provider behavior, environment requirements, public callbacks and limits from current code; clearly separate test-provider instructions from live commerce assumptions.
- [ ] Recast roles as current behavior rather than an implementation design proposal; verify role permissions, membership constraints and invite lifecycle.
- [ ] Keep links to historical design rationale where useful without presenting it as current product behavior.

### Task 3: Classify backlog, review history and active risks

**Files:**
- Modify: `docs/maintenance/technical-debt.md`, `docs/maintenance/documentation-audit.md`, `docs/ROADMAP.md`, `docs/PRIORITIES.md`, `backend/ARCHITECTURE.md`, `backend/TODO.md`, `frontend/TODO.md`
- Read: relevant code/tests/CI and dated plans under `docs/superpowers/`

- [ ] Recheck every active technical-risk row against current source and available test evidence; remove or close items fixed by recent changes, including API response consistency.
- [ ] Keep `technical-debt.md` as the single active risk register; update backend/frontend TODO and old review documents with a clear historical/non-authoritative status rather than duplicating open work.
- [ ] Mark roadmap/priority documents with status and review date; remove stale “next” checklists or preserve them as dated planning history with links to current status.
- [ ] Replace the old documentation audit with a dated record of files reviewed, evidence checked, contradictions resolved and live facts that remain unverified.
- [ ] Review retained plan/spec links and status labels; preserve historical detail unless it is incorrectly cited as current guidance.

### Task 4: Validate operations and product documentation

**Files:**
- Review: all files modified in Tasks 1–3

- [ ] Resolve relative links across active docs and retained history pages.
- [ ] Search for outdated API envelopes, N+1 status, backup/recovery status, old registration paths, stale roadmap items and duplicated active risk statements.
- [ ] Verify no command block exposes credentials, references absent files, or implies a live VPS action has already happened.
- [ ] Ensure the current risk register and audit distinguish “implemented”, “tested”, “configured on VPS”, and “not verified”.
