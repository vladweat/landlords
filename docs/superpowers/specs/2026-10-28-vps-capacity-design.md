# VPS Capacity Design

## Intent

Make the existing 2 vCPU / 4 GiB RAM / 38 GiB disk VPS more resilient when hosting a few lightweight Docker projects, without resizing the provider instance.

## Current state

The host has about 2.3 GiB memory available and 31 GiB disk available. Landlords uses about 600 MiB RAM at idle. Swap is not configured. Docker uses the `json-file` logging driver without global rotation settings.

## Approaches

- **Optimize the current VPS (chosen):** add a 2 GiB swap file, set `vm.swappiness=10`, cap Docker logs to 10 MiB per file and 3 files per container. This adds burst tolerance and bounds log growth, with a brief outage while Docker restarts and current containers are recreated.
- **Resize the VPS:** move to about 4 vCPU / 8 GiB RAM / 80 GiB disk, then apply the same log limits. This has greater steady-state capacity but requires a provider-side resize and may require a reboot.

## Scope

- Add persistent 2 GiB swap at `/swapfile` and persist `vm.swappiness=10`.
- Configure Docker's default `json-file` log rotation to `max-size=10m` and `max-file=3`.
- Restart Docker and recreate the current Landlords Compose services so the log options apply to existing containers.
- Verify swap, Docker defaults, container health, and the public HTTPS readiness endpoint.

## Constraints and risks

- Preserve Docker volumes and all application data.
- Do not alter application secrets or database contents.
- Swap is emergency headroom and is slower than RAM; it does not increase CPU or sustained memory capacity.
- Restarting Docker causes a short interruption to all containers on this VPS.
