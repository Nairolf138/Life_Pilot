#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/backup.sh [--encrypt] [--output-dir DIR] [--env-file FILE] [--skip-n8n]

Creates a timestamped compressed backup archive containing:
  - PostgreSQL dump from the docker compose postgres service
  - MinIO documents export when mc is available, otherwise the minio_data volume
  - n8n workflow/credential export when possible

Options:
  --encrypt          Encrypt the final archive with gpg symmetric encryption.
                    BACKUP_ENCRYPTION_PASSPHRASE must be set.
  --output-dir DIR   Backup destination directory (default: ./backups).
  --env-file FILE    Environment file to load (default: ./.env when present).
  --skip-n8n         Skip n8n export.
  -h, --help         Show this help.
USAGE
}

OUTPUT_DIR="${BACKUP_OUTPUT_DIR:-backups}"
ENV_FILE="${BACKUP_ENV_FILE:-.env}"
ENCRYPT=false
SKIP_N8N=false
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --encrypt) ENCRYPT=true; shift ;;
    --output-dir) [[ $# -ge 2 ]] || { echo "--output-dir requires a value" >&2; exit 1; }; OUTPUT_DIR="$2"; shift 2 ;;
    --env-file) [[ $# -ge 2 ]] || { echo "--env-file requires a value" >&2; exit 1; }; ENV_FILE="$2"; shift 2 ;;
    --skip-n8n) SKIP_N8N=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

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
require gzip

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_NAME="lifepilot-backup-$TIMESTAMP"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$OUTPUT_DIR" "$WORK_DIR/$BACKUP_NAME" "$WORK_DIR/$BACKUP_NAME/documents" "$WORK_DIR/$BACKUP_NAME/n8n"

POSTGRES_DB="${POSTGRES_DB:-lifepilot}"
POSTGRES_USER="${POSTGRES_USER:-lifepilot}"
MINIO_BUCKET="${MINIO_BUCKET:-documents}"

cat > "$WORK_DIR/$BACKUP_NAME/manifest.txt" <<MANIFEST
backup_name=$BACKUP_NAME
created_at_utc=$TIMESTAMP
postgres_db=$POSTGRES_DB
minio_bucket=$MINIO_BUCKET
MANIFEST

echo "[backup] Dumping PostgreSQL database '$POSTGRES_DB'..."
"${COMPOSE[@]}" exec -T postgres pg_dump \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --format=custom \
  --no-owner \
  --no-privileges \
  > "$WORK_DIR/$BACKUP_NAME/postgres.dump"

echo "[backup] Backing up documents..."
if "${COMPOSE[@]}" exec -T minio sh -lc 'command -v mc >/dev/null 2>&1'; then
  "${COMPOSE[@]}" exec -T minio sh -lc \
    'mc alias set local http://127.0.0.1:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null && mc mirror --overwrite "local/'"$MINIO_BUCKET"'" /tmp/lifepilot-documents-backup'
  "${COMPOSE[@]}" cp minio:/tmp/lifepilot-documents-backup/. "$WORK_DIR/$BACKUP_NAME/documents/"
  "${COMPOSE[@]}" exec -T minio rm -rf /tmp/lifepilot-documents-backup
  echo "documents_source=minio_bucket" >> "$WORK_DIR/$BACKUP_NAME/manifest.txt"
else
  "${COMPOSE[@]}" cp minio:/data/. "$WORK_DIR/$BACKUP_NAME/documents/"
  echo "documents_source=minio_volume" >> "$WORK_DIR/$BACKUP_NAME/manifest.txt"
fi

if [[ "$SKIP_N8N" == false ]]; then
  echo "[backup] Exporting n8n configuration when CLI is available..."
  if "${COMPOSE[@]}" exec -T n8n sh -lc 'command -v n8n >/dev/null 2>&1'; then
    if "${COMPOSE[@]}" exec -T n8n sh -lc 'mkdir -p /tmp/lifepilot-n8n-export && n8n export:workflow --all --output=/tmp/lifepilot-n8n-export/workflows.json && n8n export:credentials --all --decrypted=false --output=/tmp/lifepilot-n8n-export/credentials.json'; then
      "${COMPOSE[@]}" cp n8n:/tmp/lifepilot-n8n-export/. "$WORK_DIR/$BACKUP_NAME/n8n/"
      echo "n8n_export=cli" >> "$WORK_DIR/$BACKUP_NAME/manifest.txt"
    else
      echo "[backup] n8n export failed; continuing without n8n configuration." >&2
      echo "n8n_export=failed" >> "$WORK_DIR/$BACKUP_NAME/manifest.txt"
    fi
    "${COMPOSE[@]}" exec -T n8n rm -rf /tmp/lifepilot-n8n-export
  else
    echo "[backup] n8n CLI unavailable; skipping export." >&2
    echo "n8n_export=skipped_cli_unavailable" >> "$WORK_DIR/$BACKUP_NAME/manifest.txt"
  fi
else
  echo "n8n_export=skipped_by_option" >> "$WORK_DIR/$BACKUP_NAME/manifest.txt"
fi

ARCHIVE_PATH="$OUTPUT_DIR/$BACKUP_NAME.tar.gz"
echo "[backup] Compressing archive..."
tar -C "$WORK_DIR" -czf "$ARCHIVE_PATH" "$BACKUP_NAME"

if [[ "$ENCRYPT" == true ]]; then
  require gpg
  : "${BACKUP_ENCRYPTION_PASSPHRASE:?BACKUP_ENCRYPTION_PASSPHRASE is required with --encrypt}"
  echo "[backup] Encrypting archive..."
  gpg --batch --yes --symmetric --cipher-algo AES256 \
    --passphrase "$BACKUP_ENCRYPTION_PASSPHRASE" \
    --output "$ARCHIVE_PATH.gpg" "$ARCHIVE_PATH"
  rm -f "$ARCHIVE_PATH"
  ARCHIVE_PATH="$ARCHIVE_PATH.gpg"
fi

sha256sum "$ARCHIVE_PATH" > "$ARCHIVE_PATH.sha256"
echo "[backup] Created $ARCHIVE_PATH"
