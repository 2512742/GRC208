# Deploying RiskTrack on the shared VPS

RiskTrack runs on the team lead's shared Azure VM next to FieldQuire and Sentinel, following
that server's hosting guide (one shared Caddy for HTTPS, apps on `172.17.0.1:<port>` only).

| Item | Value |
|---|---|
| Address | https://thealajo.tinex.tech (A record to the VM) |
| Runs as | Docker Compose project `risktrack`, in `~/apps/risktrack` |
| Port | `172.17.0.1:9120` (reachable only through Caddy) |
| Database | SQLite in the Docker volume `risktrack_data` (the live database) |
| Remote backup | PostgreSQL on Neon (`neondb`): a full copy, refreshed after each daily backup |
| Memory limit | 384 MB |
| Site file | `~/WaterCheck/infra/sites/risktrack.caddy` (copy: `risktrack.caddy` here) |
| Backups | `~/apps/risktrack/deploy/vps/backup.sh`, daily from cron: to `~/backups/risktrack-*.db.gz` (14 days kept), then to Neon |

## Settings (`~/apps/risktrack/.env`, mode 600, created on the server only)

```
SECRET_KEY=<new random value>
DEBUG=false
DATABASE_URL=sqlite:////app/backend/data/risktrack.sqlite3
ORG_TIMEZONE=Africa/Lagos
TRUST_PROXY_HEADERS=true
BACKUP_DATABASE_URL=<Neon direct (non-pooled) URL of neondb, with sslmode=require>
```

The hosted demo password is not the README one; it lives in `~/apps/risktrack/.demo-password`
(mode 600) and is shared privately.

## Update to a new version

```bash
# on your machine, from the repository root (the app is the WS1-development/app folder)
git archive --format=tar.gz -o risktrack.tar.gz HEAD:WS1-development/app
scp -i ~/.ssh/watercheck-VM_key.pem risktrack.tar.gz azureuser@20.164.216.195:~/
# on the VM
cd ~/apps/risktrack && ~/apps/risktrack/deploy/vps/backup.sh
tar -xzf ~/risktrack.tar.gz -C ~/apps/risktrack && rm ~/risktrack.tar.gz
docker compose -f deploy/vps/docker-compose.yml --project-directory . up -d --build
```

Migrations run automatically when the container starts. Then run the hosting guide's health checks.

## Remote backup on Neon

The live database is the SQLite file. Neon keeps a full copy in PostgreSQL. After the daily
file backup, `backup.sh` runs `backup-to-postgres`, which:

1. takes a consistent snapshot of the SQLite file;
2. brings Neon up to the same schema version;
3. replaces Neon's contents in one transaction;
4. checks the row counts and the audit hash chain on the copy.

If anything fails, Neon keeps the previous copy and the log line says FAILED. The log is
`~/backups/risktrack-backup.log`.

To refresh Neon now: `$C exec app python -m app.cli backup-to-postgres --yes`.

To rebuild the live database from Neon (for example, a new VM):

```bash
C="docker compose -f deploy/vps/docker-compose.yml --project-directory ."
$C exec app python -m app.cli restore-from-backup --into /app/backend/data/restored.sqlite3
$C stop app
$C run --rm --no-deps --entrypoint sh app -c 'cd /app/backend/data && mv risktrack.sqlite3 before-restore.sqlite3 && mv restored.sqlite3 risktrack.sqlite3'
$C start app
```

## Useful commands (on the VM, in `~/apps/risktrack`)

```bash
C="docker compose -f deploy/vps/docker-compose.yml --project-directory ."
$C ps; $C logs --tail 50 app
$C exec app python -m app.cli verify-audit
$C exec app python -m app.cli reset-password --username admin --yes
$C exec -e DEMO_PASSWORD="$(cat .demo-password)" app python -m app.cli seed-demo --reset --yes   # erases data
```

## Remove

Follow the hosting guide's "Removing a project": move the site file out and reload Caddy, take a
final backup, `docker compose ... down` (add `-v` only to delete the data volume), remove the
`risktrack:latest` image by name, the folder and the cron line, then the DNS record.
