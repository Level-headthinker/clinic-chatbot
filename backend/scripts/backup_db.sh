#!/usr/bin/env bash
# Automated PostgreSQL backup for ClinicBot.
#
# Writes a timestamped, gzipped dump and prunes dumps older than the retention
# window. Designed to run on the (Linux) VPS via cron. Healthcare data — never
# run production without this scheduled.
#
# Env:
#   DATABASE_URL            postgres connection string (required)
#   BACKUP_DIR              where to write dumps   (default: /var/backups/clinicbot)
#   BACKUP_RETENTION_DAYS   prune older than this  (default: 14)
#
# Usage:   DATABASE_URL=postgres://... ./backup_db.sh
set -euo pipefail

# Load DATABASE_URL from a sibling .env if not already in the environment.
if [ -z "${DATABASE_URL:-}" ] && [ -f "$(dirname "$0")/../.env" ]; then
  export "$(grep -E '^DATABASE_URL=' "$(dirname "$0")/../.env" | head -1)"
fi
: "${DATABASE_URL:?DATABASE_URL is required}"

BACKUP_DIR="${BACKUP_DIR:-/var/backups/clinicbot}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

mkdir -p "$BACKUP_DIR"
TS="$(date +%Y%m%d_%H%M%S)"
FILE="$BACKUP_DIR/clinicbot_${TS}.sql.gz"

# --no-owner/--no-privileges make the dump portable to a fresh DB/role.
pg_dump "$DATABASE_URL" --no-owner --no-privileges | gzip > "$FILE"

SIZE="$(du -h "$FILE" | cut -f1)"
echo "✅ backup written: $FILE ($SIZE)"

# Prune old backups.
DELETED="$(find "$BACKUP_DIR" -name 'clinicbot_*.sql.gz' -mtime "+${RETENTION_DAYS}" -print -delete | wc -l)"
echo "🧹 pruned ${DELETED} backup(s) older than ${RETENTION_DAYS} days"

# OPTIONAL off-site copy (uncomment + configure — strongly recommended):
#   aws s3 cp "$FILE" "s3://your-bucket/clinicbot/"          # AWS S3
#   rclone copy "$FILE" "remote:clinicbot-backups/"          # any rclone remote
