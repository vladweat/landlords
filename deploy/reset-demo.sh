#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "$#" -ne 1 || "$1" != "--confirm" ]]; then
    cat >&2 <<'EOF'
This removes only the landlords-demo Compose project and its named volumes.
Review the target, then run: deploy/reset-demo.sh --confirm
EOF
    exit 2
fi

docker compose \
    --project-name landlords-demo \
    --file "$repo_root/docker-compose.demo.yml" \
    down --volumes --remove-orphans
