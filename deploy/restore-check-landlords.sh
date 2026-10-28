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

: "${BACKUP_DIR:?BACKUP_DIR must be set in $CONFIG_FILE}"
for command_name in docker sha256sum tar find sort tail realpath; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf '[landlords-restore-check] ERROR: required command is missing: %s\n' "$command_name" >&2
    exit 1
  }
done

log() { printf '[landlords-restore-check] %s\n' "$*"; }
fail() { log "ERROR: $*" >&2; exit 1; }

if (($# > 1)); then
  fail "usage: $0 [backup-set-directory]"
fi

backup_root=$(realpath -e -- "$BACKUP_DIR") || fail "backup directory does not exist: $BACKUP_DIR"
if (($# == 1)); then
  requested_set=$1
else
  requested_set=$(find "$backup_root" -mindepth 2 -maxdepth 2 -type f \
    -name COMPLETE -printf '%h\n' | sort | tail -n 1)
fi
[[ -n "$requested_set" ]] || fail "no completed backup sets found in $backup_root"
backup_set=$(realpath -e -- "$requested_set") || fail "backup set does not exist: $requested_set"
[[ "$backup_set" == "$backup_root"/* ]] || fail "backup set must be inside $backup_root"
[[ -d "$backup_set" && ! -L "$requested_set" ]] || fail "backup set must be a real directory"
[[ -f "$backup_set/COMPLETE" ]] || fail "backup set has no COMPLETE marker"
[[ "$(cat "$backup_set/COMPLETE")" == "complete" ]] || fail "backup set marker is invalid"
[[ -s "$backup_set/database.dump" ]] || fail "database dump is missing or empty"
[[ -s "$backup_set/documents.tar.gz" ]] || fail "documents archive is missing or empty"
[[ -f "$backup_set/SHA256SUMS" ]] || fail "checksum file is missing"

expected_manifest=$(printf '%s\n' 'database.dump' 'documents.tar.gz')
actual_manifest=$(awk '{print $2}' "$backup_set/SHA256SUMS" | sort)
[[ "$actual_manifest" == "$expected_manifest" ]] || fail "checksum manifest has unexpected files"
(cd "$backup_set" && sha256sum --check --strict --status SHA256SUMS) \
  || fail "backup checksum verification failed"
tar -tzf "$backup_set/documents.tar.gz" >/dev/null \
  || fail "documents archive is invalid"

docker image inspect postgres:15 >/dev/null 2>&1 \
  || fail "local postgres:15 image is required; refusing an implicit network pull"

run_id="$(date -u +%s)-$$-$(date -u +%N)"
container_name="landlords-restore-check-$run_id"
volume_name="$container_name-data"
label_key=io.landlords.restore-check
if docker inspect "$container_name" >/dev/null 2>&1 \
  || docker volume inspect "$volume_name" >/dev/null 2>&1; then
  fail "temporary Docker resource name collision"
fi

cleanup() {
  status=$?
  trap - EXIT
  container_label=$(docker inspect -f "{{ index .Config.Labels \"$label_key\" }}" \
    "$container_name" 2>/dev/null || true)
  if [[ "$container_label" == "$run_id" ]]; then
    docker rm -f "$container_name" >/dev/null 2>&1 \
      || log "WARNING: could not remove temporary container $container_name"
  fi
  volume_label=$(docker volume inspect -f "{{ index .Labels \"$label_key\" }}" \
    "$volume_name" 2>/dev/null || true)
  if [[ "$volume_label" == "$run_id" ]]; then
    docker volume rm "$volume_name" >/dev/null 2>&1 \
      || log "WARNING: could not remove temporary volume $volume_name"
  fi
  exit "$status"
}
trap cleanup EXIT

docker volume create --label "$label_key=$run_id" "$volume_name" >/dev/null \
  || fail "could not create temporary restore volume"
docker run -d --name "$container_name" --label "$label_key=$run_id" \
  --network none -v "$volume_name:/var/lib/postgresql/data" \
  -e POSTGRES_HOST_AUTH_METHOD=trust postgres:15 >/dev/null \
  || fail "could not start isolated PostgreSQL container"

ready=0
for ((attempt = 1; attempt <= 60; attempt++)); do
  if docker exec "$container_name" pg_isready -U postgres -d postgres >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
(( ready == 1 )) || fail "temporary PostgreSQL did not become ready"

log "Restoring backup into isolated PostgreSQL"
docker exec -i "$container_name" pg_restore -U postgres -d postgres \
  --no-owner --no-acl <"$backup_set/database.dump" \
  || fail "pg_restore failed in isolated PostgreSQL"

table_count=$(docker exec "$container_name" psql -U postgres -d postgres \
  -Atqc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'") \
  || fail "could not inspect restored database"
[[ "$table_count" =~ ^[0-9]+$ ]] && (( table_count > 0 )) \
  || fail "restored database has no public tables"

log "Restore check passed: $table_count public tables; documents archive is readable"
