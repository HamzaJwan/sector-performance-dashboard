# Sector Analysis — Runbook (Restore-Safe)

## Overview
This repo runs a daily collector (`collect_stats.py`) that:
- reads Zabbix metrics
- stores sector KPIs into MariaDB (Sectors DB)
- the web UI reads from the same DB

## One-time setup on a new server
1) Place project at:
   - `/opt/sector_analysis`

2) Ensure DB container exists (optional but recommended):
   - Container name: `sectors-db`
   - Port mapping: `3307 -> 3306`

3) Create python venv & install requirements (if not already):
   - `./venv/bin/python -V`
   - `./venv/bin/pip install -r requirements.txt`

4) Run bootstrap once (installs systemd + timer + db init):
   - `sudo /opt/sector_analysis/scripts/bootstrap.sh`

## Daily schedule
- systemd timer: `sector-collector.timer`
- runs daily at `01:00` (server local time)

Check:
- `systemctl list-timers --all | grep sector-collector`

## Restore procedure (the goal)
If you restore ONLY the folder:
- `/opt/sector_analysis`

Then do:
- `reboot`

On boot:
- `sector-bootstrap.service` runs
- it re-installs timer + ensures DB tables
- next scheduled run resumes automatically

## Manual run / troubleshooting
Run now:
- `sudo systemctl start sector-collector.service`

Logs:
- `/opt/sector_analysis/collect_stats.log`
- `tail -n 100 /opt/sector_analysis/collect_stats.log`

Verify DB container:
- `docker ps | grep sectors-db`
