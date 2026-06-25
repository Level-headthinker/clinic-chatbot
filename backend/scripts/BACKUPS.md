# Database Backups — runbook

This is **healthcare data**. A disk failure or bad migration without backups
means every clinic loses their patients. Treat this as mandatory before launch.

## What's here
| Script | Purpose |
|---|---|
| `backup_db.sh` | Timestamped, gzipped `pg_dump` + prune old dumps |
| `restore_db.sh` | Restore a dump into the `DATABASE_URL` database (destructive) |

## One-time setup (on the VPS)
1. Ensure `pg_dump` / `psql` are installed (`apt install postgresql-client`).
2. Make the scripts executable:
   ```bash
   chmod +x backend/scripts/backup_db.sh backend/scripts/restore_db.sh
   ```
3. Pick a backup directory and retention, e.g. `/var/backups/clinicbot`, 14 days.

## Run a backup manually
```bash
DATABASE_URL='postgres://user:pass@host:5432/clinicbot' \
BACKUP_DIR=/var/backups/clinicbot \
BACKUP_RETENTION_DAYS=14 \
./backend/scripts/backup_db.sh
```
(If `DATABASE_URL` isn't set, the script reads it from `backend/.env`.)

## Schedule it (daily at 03:00) — cron
```bash
crontab -e
```
Add:
```
0 3 * * *  BACKUP_DIR=/var/backups/clinicbot BACKUP_RETENTION_DAYS=14 /path/to/backend/scripts/backup_db.sh >> /var/log/clinicbot-backup.log 2>&1
```

## ⚠️ Off-site copies (do this)
A backup on the same server doesn't survive losing the server. Uncomment one of
the lines at the end of `backup_db.sh` to push each dump off-site:
- `aws s3 cp` to an S3 bucket, or
- `rclone copy` to Google Drive / Backblaze / any remote.

## Test the restore (do this BEFORE you need it)
A backup you've never restored is not a backup. Verify into a **scratch** DB:
```bash
# 1. create a throwaway database
createdb clinicbot_restore_test

# 2. restore the latest dump into it (NOT production)
DATABASE_URL='postgres://user:pass@host:5432/clinicbot_restore_test' \
./backend/scripts/restore_db.sh /var/backups/clinicbot/clinicbot_YYYYmmdd_HHMMSS.sql.gz

# 3. sanity-check a few tables, then drop it
psql 'postgres://.../clinicbot_restore_test' -c "select count(*) from patients;"
dropdb clinicbot_restore_test
```

## Restoring production (only in a real disaster)
1. Stop the backend (so nothing writes mid-restore).
2. `restore_db.sh` into the production `DATABASE_URL` (it asks for `yes`).
3. Start the backend; verify login + a clinic's data.

## Recommended cadence
- **Daily** automated dump, **14-day** retention on the server.
- **Off-site** copy of each dump (S3/rclone).
- **Monthly** test restore into a scratch DB.
- Managed Postgres (e.g. the VPS provider's) often adds point-in-time recovery —
  use it in addition to these dumps, not instead of.
