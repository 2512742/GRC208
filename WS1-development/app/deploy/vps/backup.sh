#!/usr/bin/env bash
# Daily RiskTrack backup on the shared VPS:
# 1. a consistent SQLite copy (online backup API, safe while the app runs) to
#    ~/backups/risktrack-YYYYmmdd-HHMM.db.gz, keeping 14 days;
# 2. when BACKUP_DATABASE_URL is set in .env, a full refresh of the remote PostgreSQL backup
#    (Neon). A failure there is reported but never undoes the file backup.
set -euo pipefail
cd "$HOME/apps/risktrack"
compose() { docker compose -f deploy/vps/docker-compose.yml --project-directory . "$@" </dev/null; }
stamp=$(date +%Y%m%d-%H%M)
tmp=/app/backend/data/backup-$stamp.db
compose exec -T app python -c "import sqlite3; s=sqlite3.connect('/app/backend/data/risktrack.sqlite3'); d=sqlite3.connect('$tmp'); s.backup(d); d.close(); s.close()"
mkdir -p "$HOME/backups"
compose cp "app:$tmp" "$HOME/backups/risktrack-$stamp.db"
compose exec -T app rm -f "$tmp"
gzip -f "$HOME/backups/risktrack-$stamp.db"
find "$HOME/backups" -maxdepth 1 -name 'risktrack-*.db.gz' -mtime +14 -delete
echo "$(date -Is) risktrack backup ok: risktrack-$stamp.db.gz"
if grep -q '^BACKUP_DATABASE_URL=.' .env 2>/dev/null; then
  if out=$(compose exec -T app python -m app.cli backup-to-postgres --yes 2>&1); then
    echo "$(date -Is) risktrack remote backup ok: $(echo "$out" | tail -1)"
  else
    echo "$(date -Is) risktrack remote backup FAILED: $(echo "$out" | tail -1)"
    exit 1
  fi
fi
