#!/usr/bin/env bash
# Restore a ClinicBot PostgreSQL backup produced by backup_db.sh.
#
# ⚠️  DESTRUCTIVE: this overwrites the target database with the dump's contents.
# Always restore into a SCRATCH database first to verify, before touching prod.
#
# Env:    DATABASE_URL   target postgres connection string (required)
# Usage:  DATABASE_URL=postgres://... ./restore_db.sh /path/clinicbot_YYYYmmdd_HHMMSS.sql.gz
set -euo pipefail

FILE="${1:?usage: restore_db.sh <backup_file.sql.gz>}"
[ -f "$FILE" ] || { echo "❌ file not found: $FILE"; exit 1; }

if [ -z "${DATABASE_URL:-}" ] && [ -f "$(dirname "$0")/../.env" ]; then
  export "$(grep -E '^DATABASE_URL=' "$(dirname "$0")/../.env" | head -1)"
fi
: "${DATABASE_URL:?DATABASE_URL is required}"

echo "⚠️  This will OVERWRITE the database at DATABASE_URL with:"
echo "    $FILE"
read -r -p "Type 'yes' to proceed: " confirm
[ "$confirm" = "yes" ] || { echo "aborted"; exit 1; }

gunzip -c "$FILE" | psql "$DATABASE_URL" -v ON_ERROR_STOP=1
echo "✅ restore complete"
