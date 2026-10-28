# VPS Capacity Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add burst-memory headroom and bounded Docker logs on the current VPS so it can host several lightweight projects more safely.

**Architecture:** Persist a 2 GiB `/swapfile` with `vm.swappiness=10`, then set Docker's default `json-file` rotation to 10 MiB × 3 files. Restart Docker and recreate Landlords services so existing containers inherit the log settings.

**Tech Stack:** Ubuntu 24.04, systemd, Docker Engine, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-10-28-vps-capacity-design.md`

## Global Constraints

- Preserve Docker volumes and all application data.
- Do not alter application secrets or database contents.
- Add exactly 2 GiB of swap and set `vm.swappiness=10`.
- Configure Docker `json-file` logs with `max-size=10m` and `max-file=3`.
- Expect brief downtime during Docker restart and container recreation.

## Review Focus

- Existing swap: inspect before adding; do not create a duplicate swap entry.
- Disk headroom: confirm at least 2 GiB free before allocating `/swapfile`.
- Existing Docker daemon config: preserve unrelated keys when adding log options.
- Existing containers: recreate them after daemon configuration so rotation applies.
- Application recovery: confirm database and Redis volumes remain healthy and HTTPS `/ready` returns 200.

---

### Task 1: Add persistent swap

**Files:**
- Create: `/swapfile` (2 GiB, mode 0600)
- Create: `/etc/sysctl.d/99-vps-capacity.conf` (`vm.swappiness=10`)
- Modify: `/etc/fstab` with one `/swapfile` entry

- [x] Confirm no active swap or existing `/swapfile`, and confirm at least 2 GiB disk space is available.
- [x] Create and secure the swap file, run `mkswap`, and activate it with `swapon`.
- [x] Persist the swap entry and swappiness setting.
- [x] Verify `swapon --show` reports 2 GiB and `sysctl vm.swappiness` reports 10.

### Task 2: Bound Docker logs and restore the project

**Files:**
- Create or modify: `/etc/docker/daemon.json` with the default `json-file` driver and rotation options.

- [x] Preserve existing daemon configuration and set `max-size=10m`, `max-file=3`.
- [x] Validate the JSON before restarting Docker.
- [x] Restart Docker and recreate the production Compose stack without the development override.
- [x] Verify Docker reports the new defaults, Landlords services are healthy, PostgreSQL and Redis have no public host ports, and `https://landlords.wvzl.site/ready` returns 200.
