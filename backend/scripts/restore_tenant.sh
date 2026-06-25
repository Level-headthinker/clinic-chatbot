#!/usr/bin/env bash
# Restore ONE clinic (tenant) from a full backup, WITHOUT touching other clinics.
#
# The whole-DB restore (restore_db.sh) would roll every clinic back to the backup
# time. This does it surgically: it loads the backup into a throwaway scratch DB,
# then copies just the one tenant's rows back into production.
#
# Strategy (safe, repeatable):
#   1. Restore the dump into a fresh scratch database.
#   2. From the scratch DB, COPY OUT only rows WHERE tenant_id = <id>, per table.
#   3. COPY them INTO production (append). Existing prod rows are not deleted.
#
# ⚠️  This APPENDS the tenant's rows from the backup into production. If a row
#     with the same primary key already exists, that table's load is skipped with
#     a notice (ON_ERROR_STOP keeps it safe). Review the report at the end.
#
# Env:
#   PROD_DATABASE_URL     production connection string (required)
#   SCRATCH_DATABASE_URL  empty scratch DB to restore the dump into (required)
# Usage:
#   PROD_DATABASE_URL=... SCRATCH_DATABASE_URL=... \
#     ./restore_tenant.sh <backup_file.sql.gz> <tenant_id>
set -euo pipefail

FILE="${1:?usage: restore_tenant.sh <backup_file.sql.gz> <tenant_id>}"
TENANT="${2:?usage: restore_tenant.sh <backup_file.sql.gz> <tenant_id>}"
[ -f "$FILE" ] || { echo "❌ file not found: $FILE"; exit 1; }
: "${PROD_DATABASE_URL:?PROD_DATABASE_URL is required}"
: "${SCRATCH_DATABASE_URL:?SCRATCH_DATABASE_URL is required (an empty throwaway DB)}"

# Tables that carry tenant_id, in FK-safe insert order (parents before children).
TABLES=(
  patients doctors services rooms
  chat_sessions leads
  appointments visit_records invoices
  prescriptions notes follow_ups treatment_sessions
  knowledge_base audit_logs
)

echo "⚠️  Restoring tenant $TENANT from $FILE into production."
echo "    Scratch DB: $SCRATCH_DATABASE_URL"
read -r -p "Type 'yes' to proceed: " confirm
[ "$confirm" = "yes" ] || { echo "aborted"; exit 1; }

echo "1/3  Loading backup into scratch DB…"
gunzip -c "$FILE" | psql "$SCRATCH_DATABASE_URL" -v ON_ERROR_STOP=1 -q

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "2/3  Extracting tenant rows from scratch DB…"
for t in "${TABLES[@]}"; do
  psql "$SCRATCH_DATABASE_URL" -At -c \
    "\copy (SELECT * FROM ${t} WHERE tenant_id = '${TENANT}') TO '${WORK}/${t}.csv' WITH CSV" \
    2>/dev/null || echo "   (skip ${t}: not in backup)"
done

echo "3/3  Loading tenant rows into production…"
for t in "${TABLES[@]}"; do
  [ -s "${WORK}/${t}.csv" ] || { echo "   ${t}: 0 rows"; continue; }
  n="$(wc -l < "${WORK}/${t}.csv")"
  if psql "$PROD_DATABASE_URL" -v ON_ERROR_STOP=1 -q -c \
       "\copy ${t} FROM '${WORK}/${t}.csv' WITH CSV" 2>/tmp/restore_tenant_err; then
    echo "   ${t}: +${n} rows"
  else
    echo "   ⚠️  ${t}: load failed (likely existing rows / FK) — review:"
    sed 's/^/        /' /tmp/restore_tenant_err
  fi
done

echo "✅ tenant restore complete. Verify the clinic's data in production."
echo "   Tip: drop the scratch DB when done — it held every clinic's data."
