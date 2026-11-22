#!/usr/bin/env bash
# Daily RiskTrack backup on the shared VPS: a consistent SQLite copy (online backup API, safe
# while the app runs) to ~/backups/risktrack-YYYYmmdd-HHMM.db.gz, keeping 14 days.
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
