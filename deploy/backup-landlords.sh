#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

CONFIG_FILE=${BACKUP_CONFIG_FILE:-/etc/landlords-backup.conf}
if [[ -r "$CONFIG_FILE" ]]; then
  # This file is root-owned and mode 0600 when installed by the runbook.
  # shellcheck disable=SC1090
  set -a
  source "$CONFIG_FILE"
  set +a
fi

: "${PROJECT_DIR:?PROJECT_DIR must be set in $CONFIG_FILE}"
: "${BACKUP_DIR:?BACKUP_DIR must be set in $CONFIG_FILE}"

RETENTION_DAYS=${RETENTION_DAYS:-14}
MIN_FREE_MB=${MIN_FREE_MB:-256}
COMPOSE_PROJECT=${COMPOSE_PROJECT:-landlords}
COMPOSE_FILES=(
  "$PROJECT_DIR/docker-compose.yml"
  "$PROJECT_DIR/docker-compose.production.yml"
)

log() { printf '[landlords-backup] %s\n' "$*"; }
fail() { log "ERROR: $*" >&2; exit 1; }

for command_name in docker tar sha256sum flock df awk find grep; do
  command -v "$command_name" >/dev/null 2>&1 || fail "required command is missing: $command_name"
done
[[ "$RETENTION_DAYS" =~ ^[1-9][0-9]*$ ]] || fail "RETENTION_DAYS must be a positive integer"
[[ "$MIN_FREE_MB" =~ ^[1-9][0-9]*$ ]] || fail "MIN_FREE_MB must be a positive integer"
[[ -d "$PROJECT_DIR" ]] || fail "project directory does not exist: $PROJECT_DIR"
for compose_file in "${COMPOSE_FILES[@]}"; do
  [[ -r "$compose_file" ]] || fail "Compose file is not readable: $compose_file"
done

mkdir -p -- "$BACKUP_DIR"
chmod 0700 -- "$BACKUP_DIR"
exec 9>"$BACKUP_DIR/.backup.lock"
flock -n 9 || fail "another backup is already running"

free_kb=$(df -Pk -- "$BACKUP_DIR" | awk 'NR == 2 { print $4 }')
[[ "$free_kb" =~ ^[0-9]+$ ]] || fail "cannot determine free space for $BACKUP_DIR"
(( free_kb >= MIN_FREE_MB * 1024 )) || fail "less than ${MIN_FREE_MB} MiB free in $BACKUP_DIR"

compose() {
  docker compose --project-directory "$PROJECT_DIR" \
    -p "$COMPOSE_PROJECT" \
    -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" "$@"
}

compose config --quiet || fail "Compose configuration is invalid"
running_services=$(compose ps --services --status running) || fail "cannot inspect Compose services"
grep -Fxq postgres <<<"$running_services" || fail "PostgreSQL Compose service is not running"

stamp=$(date -u +%Y%m%dT%H%M%SZ)
final_dir="$BACKUP_DIR/landlords-$stamp"
[[ ! -e "$final_dir" ]] || fail "backup set already exists: $final_dir"
temp_dir=$(mktemp -d "$BACKUP_DIR/.landlords-tmp-XXXXXXXX")
cleanup() {
  status=$?
  trap - EXIT
  if [[ -n "${temp_dir:-}" && -d "$temp_dir" ]]; then
    rm -rf -- "$temp_dir"
  fi
  exit "$status"
}
trap cleanup EXIT

log "Creating PostgreSQL dump"
compose exec -T postgres sh -ec 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  >"$temp_dir/database.dump" || fail "pg_dump failed"
[[ -s "$temp_dir/database.dump" ]] || fail "pg_dump produced an empty file"

log "Archiving documents"
documents_dir="$PROJECT_DIR/storage/documents"
if [[ -d "$documents_dir" ]]; then
  tar -czf "$temp_dir/documents.tar.gz" -C "$PROJECT_DIR/storage" documents \
    || fail "documents archive failed"
else
  mkdir -p "$temp_dir/empty/documents"
  tar -czf "$temp_dir/documents.tar.gz" -C "$temp_dir/empty" documents \
    || fail "empty documents archive failed"
fi
tar -tzf "$temp_dir/documents.tar.gz" >/dev/null || fail "documents archive is invalid"

(cd "$temp_dir" && sha256sum database.dump documents.tar.gz > SHA256SUMS)
printf 'complete\n' >"$temp_dir/COMPLETE"
chmod 0600 "$temp_dir/database.dump" "$temp_dir/documents.tar.gz" \
  "$temp_dir/SHA256SUMS" "$temp_dir/COMPLETE"
mv -- "$temp_dir" "$final_dir"
temp_dir=
log "Published backup set: $final_dir"

cutoff=$((RETENTION_DAYS))
while IFS= read -r -d '' old_dir; do
  if [[ -f "$old_dir/COMPLETE" ]]; then
    log "Removing expired completed set: $old_dir"
    rm -rf -- "$old_dir"
  fi
done < <(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d \
  -name 'landlords-*' -mtime "+$cutoff" -print0)

log "Backup completed successfully"
