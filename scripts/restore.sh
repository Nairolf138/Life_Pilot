#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/restore.sh BACKUP_ARCHIVE [--decrypt] [--env-file FILE] [--yes]

Restores a Life Pilot backup created by scripts/backup.sh:
  - PostgreSQL custom dump into the docker compose postgres service
  - documents into MinIO when mc is available, otherwise into the minio_data volume
  - minimal post-restore checks for PostgreSQL and document backup contents

Options:
  --decrypt        Decrypt BACKUP_ARCHIVE with gpg first. BACKUP_ENCRYPTION_PASSPHRASE must be set.
  --env-file FILE  Environment file to load (default: ./.env when present).
  --yes            Do not prompt for destructive restore confirmation.
  -h, --help       Show this help.
USAGE
}

[[ $# -gt 0 ]] || { usage >&2; exit 1; }
ARCHIVE=""
ENV_FILE="${BACKUP_ENV_FILE:-.env}"
DECRYPT=false
ASSUME_YES=false
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --decrypt) DECRYPT=true; shift ;;
    --env-file) [[ $# -ge 2 ]] || { echo "--env-file requires a value" >&2; exit 1; }; ENV_FILE="$2"; shift 2 ;;
    --yes) ASSUME_YES=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) [[ -z "$ARCHIVE" ]] || { echo "Unexpected argument: $1" >&2; exit 1; }; ARCHIVE="$1"; shift ;;
  esac
done
[[ -n "$ARCHIVE" ]] || { echo "BACKUP_ARCHIVE is required" >&2; exit 1; }

cd "$PROJECT_DIR"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

require() { command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }; }
require docker
require tar

POSTGRES_DB="${POSTGRES_DB:-lifepilot}"
POSTGRES_USER="${POSTGRES_USER:-lifepilot}"
MINIO_BUCKET="${MINIO_BUCKET:-documents}"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

RESTORE_ARCHIVE="$ARCHIVE"
if [[ "$DECRYPT" == true ]]; then
  require gpg
  : "${BACKUP_ENCRYPTION_PASSPHRASE:?BACKUP_ENCRYPTION_PASSPHRASE is required with --decrypt}"
  RESTORE_ARCHIVE="$WORK_DIR/backup.tar.gz"
  gpg --batch --yes --decrypt --passphrase "$BACKUP_ENCRYPTION_PASSPHRASE" \
    --output "$RESTORE_ARCHIVE" "$ARCHIVE"
fi

if [[ "$ASSUME_YES" == false ]]; then
  read -r -p "This will overwrite database '$POSTGRES_DB' and documents. Type RESTORE to continue: " CONFIRM
  [[ "$CONFIRM" == "RESTORE" ]] || { echo "Restore cancelled."; exit 1; }
fi

tar -C "$WORK_DIR" -xzf "$RESTORE_ARCHIVE"
BACKUP_ROOT="$(find "$WORK_DIR" -mindepth 1 -maxdepth 1 -type d -name 'lifepilot-backup-*' | head -n 1)"
[[ -n "$BACKUP_ROOT" && -f "$BACKUP_ROOT/postgres.dump" ]] || { echo "Invalid backup archive" >&2; exit 1; }

echo "[restore] Restoring PostgreSQL database '$POSTGRES_DB'..."
"${COMPOSE[@]}" exec -T postgres dropdb --username "$POSTGRES_USER" --if-exists "$POSTGRES_DB"
"${COMPOSE[@]}" exec -T postgres createdb --username "$POSTGRES_USER" "$POSTGRES_DB"
"${COMPOSE[@]}" exec -T postgres pg_restore \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --clean --if-exists --no-owner --no-privileges \
  < "$BACKUP_ROOT/postgres.dump"

echo "[restore] Restoring documents..."
if [[ -d "$BACKUP_ROOT/documents" ]]; then
  if "${COMPOSE[@]}" exec -T minio sh -lc 'command -v mc >/dev/null 2>&1'; then
    "${COMPOSE[@]}" exec -T minio rm -rf /tmp/lifepilot-documents-restore
    "${COMPOSE[@]}" cp "$BACKUP_ROOT/documents/." minio:/tmp/lifepilot-documents-restore/
    "${COMPOSE[@]}" exec -T minio sh -lc \
      'mc alias set local http://127.0.0.1:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null && mc mb --ignore-existing "local/'"$MINIO_BUCKET"'" && mc mirror --overwrite /tmp/lifepilot-documents-restore "local/'"$MINIO_BUCKET"'"'
    "${COMPOSE[@]}" exec -T minio rm -rf /tmp/lifepilot-documents-restore
  else
    "${COMPOSE[@]}" exec -T minio sh -lc 'find /data -mindepth 1 -maxdepth 1 -exec rm -rf {} +'
    "${COMPOSE[@]}" cp "$BACKUP_ROOT/documents/." minio:/data/
  fi
fi

echo "[restore] Running minimal post-restore checks..."
"${COMPOSE[@]}" exec -T postgres pg_isready --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"
"${COMPOSE[@]}" exec -T postgres psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --tuples-only --command 'select count(*) from information_schema.tables;' >/dev/null
DOC_COUNT="$(find "$BACKUP_ROOT/documents" -type f | wc -l | tr -d ' ')"
[[ "$DOC_COUNT" =~ ^[0-9]+$ ]] || { echo "Unable to count restored documents" >&2; exit 1; }
echo "[restore] PostgreSQL is reachable and backup contained $DOC_COUNT document file(s)."
