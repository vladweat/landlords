# Backup and Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create daily local backups of the Landlords PostgreSQL database and document files, with retention and an isolated PostgreSQL restore check.

**Architecture:** Host-side Bash scripts run under systemd. The backup script uses the production Compose project to stream a PostgreSQL custom dump, archives `storage/documents`, writes checksums and publishes complete backup sets atomically. A separate weekly service restores the latest set to a disposable PostgreSQL 15 container with no published port; production volumes and services are untouched.

**Tech Stack:** Bash, Docker Compose v2, PostgreSQL 15 `pg_dump`/`pg_restore`, systemd timer.

**Spec:** `docs/superpowers/specs/2026-10-28-backup-recovery-design.md`

## Global Constraints

- Store local backup sets in `/var/backups/landlords`; keep 14 days.
- Save PostgreSQL in custom format and `storage/documents` separately.
- Install files root-owned with restrictive permissions; never include application secrets in archives.
- Do not publish a port for restore-check containers or attach them to production networks.
- Never run destructive restore commands against the live PostgreSQL volume.
- Do not add S3 credentials, purchase storage, or claim off-site protection.

## Review Focus

- Interrupted dump/archive must not appear as a valid completed backup; test failure cleanup and atomic publication.
- Missing or empty documents directory must be handled predictably; test empty directory archive and archive listing.
- Incorrect/tampered checksum or invalid dump must make restore-check fail without changing production; verify with an isolated corrupted copy.
- Retention must only delete this project's old, completed backup sets; test with an unrelated sentinel file and an expired backup set.
- Timer must run after downtime and invoke the same locked script; verify service/timer state and `Persistent=true`.

---

### Task 1: Host backup and isolated restore-check scripts

**Files:**
- Create: `deploy/backup-landlords.sh`
- Create: `deploy/restore-check-landlords.sh`
- Test: `deploy/tests/test_backup_scripts.py`

**Interfaces:**
- `backup-landlords.sh`: read `PROJECT_DIR` and `BACKUP_DIR` from `/etc/landlords-backup.conf` (override paths only for manual checks); produce a timestamped set containing `database.dump`, `documents.tar.gz`, `SHA256SUMS`, and `COMPLETE`.
- `restore-check-landlords.sh`: accept an optional backup-set directory, default to newest complete set; return nonzero on checksum, dump restore, or document archive failure; only remove the uniquely named temporary container/volume that it created.

- [x] **Step 1: Write behavioral tests for backup publication and cleanup**

  Add `deploy/tests/test_backup_scripts.py` using Python's standard library and a narrow fake `docker` executable. Assert that a successful run publishes a checksummed, owner-only set with documents; a failed dump leaves no completed or temporary set; and retention removes only expired completed `landlords-*` sets while preserving an unrelated sentinel.

- [x] **Step 2: Run the backup tests to verify RED**

  Run: `python3 -m unittest deploy.tests.test_backup_scripts -v`
  Expected: the success and retention tests fail because the backup script is absent; the failure test must also fail because it detects the absent script rather than a simulated dump error.

- [x] **Step 3: Implement backup script preflight and atomic set creation**

  Require Docker Compose v2, readable project configuration, running PostgreSQL, sufficient free space, and a writable backup directory. Use `flock` to prevent overlap. Build into a private temporary directory under `BACKUP_DIR`, calculate SHA-256, write `COMPLETE` last, then rename to the timestamped final directory. On failure remove only the temporary directory and exit nonzero.

- [x] **Step 4: Run backup tests and validate syntax**

  Run: `python3 -m unittest deploy.tests.test_backup_scripts -v`
  Expected: 3 tests pass. Also run `bash -n deploy/backup-landlords.sh`.

- [x] **Step 5: Write a failing restore-check validation test**

  Add a test that gives the checker a tampered backup set and asserts it exits nonzero before calling the fake Docker executable. Run the unittest module and confirm it fails because the restore-check script is absent.

- [x] **Step 6: Implement isolated restore-check**

  Verify `COMPLETE` and `SHA256SUMS`, inspect the custom dump, start an ephemeral `postgres:15` container with `--network none`, no published ports, and a uniquely named temporary volume/container; wait for readiness; restore with `pg_restore --no-owner --no-acl`; assert expected public schema objects exist; validate document archive with `tar -tzf`; clean up only resources named by this run, including on errors.

- [x] **Step 7: Validate restore-check failure paths**

  Run `bash -n deploy/restore-check-landlords.sh`. Against a disposable copy of a valid set, corrupt the dump and separately alter the checksum; each check must fail and production container/volumes must remain unchanged.

### Task 2: systemd schedule, runbook, and safe VPS activation

**Files:**
- Create: `deploy/landlords-backup.service`
- Create: `deploy/landlords-backup.timer`
- Create: `deploy/landlords-restore-check.service`
- Create: `deploy/landlords-restore-check.timer`
- Modify: `docs/deploy.md`

**Interfaces:**
- Backup service runs as root from `PROJECT_DIR`, reads `/etc/landlords-backup.conf`, and invokes `deploy/backup-landlords.sh`.
- Backup timer runs daily at 02:30 UTC with `Persistent=true` and up to five minutes randomized delay.
- Restore-check timer runs weekly on Sunday after the daily backup window.
- Runbook documents install, status/log inspection, retention, restore to a separate clean database, and the explicit off-site limitation.

- [x] **Step 1: Add systemd oneshot services and persistent timers**

  Set `User=root`, `UMask=0077`, `EnvironmentFile=/etc/landlords-backup.conf`, and `Requires=docker.service`. `ExecStart` invokes the script under `${PROJECT_DIR}`; the script passes `--project-directory` to Compose and does not depend on the service working directory. The restore-check service runs against the latest completed set.

- [x] **Step 2: Verify unit files and runbook instructions**

  Run `systemd-analyze verify` on the unit files. Review the recovery commands to confirm they name a new/empty target database and do not issue `--clean` against the configured production service.

- [x] **Step 3: Install configuration and unit files on the VPS**

  Create `/etc/landlords-backup.conf` with `PROJECT_DIR=/root/projects/landlords` and `BACKUP_DIR=/var/backups/landlords`, mode `0600`; install scripts/units root-owned; load the config via `EnvironmentFile` and use `${PROJECT_DIR}` in `ExecStart`; reload systemd and enable/start both timers. Do not restart application services.

- [x] **Step 4: Run and verify the first backup and isolated restore-check**

  Start the backup service once, then the restore-check service. Confirm a completed set exists with checksums, restore-check exits zero, only its temporary resources are removed, production API/PostgreSQL containers remain healthy, and timer next-run times are shown by `systemctl list-timers`.

- [x] **Step 5: Confirm retention guard without deleting real backups**

  Exercise age selection against a temporary backup directory containing an expired synthetic set plus an unrelated sentinel; confirm only the synthetic set is eligible for removal.
