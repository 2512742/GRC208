# Deploying RiskTrack on the shared VPS

RiskTrack runs on the team lead's shared Azure VM next to FieldQuire and Sentinel, following
that server's hosting guide (one shared Caddy for HTTPS, apps on `172.17.0.1:<port>` only).

| Item | Value |
|---|---|
| Address | https://thealajo.tinex.tech (A record to the VM) |
| Runs as | Docker Compose project `risktrack`, in `~/apps/risktrack` |
| Port | `172.17.0.1:9120` (reachable only through Caddy) |
| Database | SQLite in the Docker volume `risktrack_data` |
| Memory limit | 384 MB |
| Site file | `~/WaterCheck/infra/sites/risktrack.caddy` (copy: `risktrack.caddy` here) |
| Backups | `~/apps/risktrack/deploy/vps/backup.sh`, daily from cron, to `~/backups/risktrack-*.db.gz`, 14 days kept |

## Settings (`~/apps/risktrack/.env`, mode 600, created on the server only)

```
SECRET_KEY=<new random value>
DEBUG=false
DATABASE_URL=sqlite:////app/backend/data/risktrack.sqlite3
ORG_TIMEZONE=Africa/Lagos
TRUST_PROXY_HEADERS=true
```

The hosted demo password is not the README one; it lives in `~/apps/risktrack/.demo-password`
(mode 600) and is shared privately.

## Update to a new version

```bash
# on your machine, from the repository
git archive --format=tar.gz -o risktrack.tar.gz HEAD
scp -i ~/.ssh/watercheck-VM_key.pem risktrack.tar.gz azureuser@20.164.216.195:~/
# on the VM
cd ~/apps/risktrack && ~/apps/risktrack/deploy/vps/backup.sh
tar -xzf ~/risktrack.tar.gz -C ~/apps/risktrack && rm ~/risktrack.tar.gz
docker compose -f deploy/vps/docker-compose.yml --project-directory . up -d --build
```

Migrations run automatically when the container starts. Then run the hosting guide's health checks.

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
