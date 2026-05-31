#!/bin/bash
# Daily database backup script
# Add to cron: 0 2 * * * /path/to/clinic-chatbot/backup.sh

set -e

BACKUP_DIR="/root/backups"
DATE=$(date +%Y%m%d_%H%M%S)
CONTAINER="clinic-chatbot-db-1"
DB_NAME="clinicbot"
DB_USER="clinicbot"

mkdir -p "$BACKUP_DIR"

# Create backup
docker exec "$CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_DIR/backup_$DATE.sql"

# Compress it
gzip "$BACKUP_DIR/backup_$DATE.sql"

# Delete backups older than 30 days
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +30 -delete

echo "Backup saved: $BACKUP_DIR/backup_$DATE.sql.gz"
