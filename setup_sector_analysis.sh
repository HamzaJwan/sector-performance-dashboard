#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/sector_analysis"
PY="$APP_DIR/venv/bin/python"
COLLECT="$APP_DIR/collect_stats.py"

SERVICE_FILE="/etc/systemd/system/sector-collector.service"
TIMER_FILE="/etc/systemd/system/sector-collector.timer"

LOG_FILE="$APP_DIR/collect_stats.log"
TZ_NAME="Africa/Tripoli"

echo "[setup] starting..."

# 0) sanity
if [[ ! -f "$COLLECT" ]]; then
  echo "[setup] ERROR: $COLLECT not found"
  exit 1
fi
if [[ ! -x "$PY" ]]; then
  echo "[setup] ERROR: venv python not found at $PY"
  exit 1
fi

# 1) Ensure timezone (best for "01:00 Libya time")
if command -v timedatectl >/dev/null 2>&1; then
  timedatectl set-timezone "$TZ_NAME" >/dev/null 2>&1 || true
fi

# 2) Ensure sectors-db container is running (if exists)
if command -v docker >/dev/null 2>&1; then
  if docker ps -a --format '{{.Names}}' | grep -qx 'sectors-db'; then
    if ! docker ps --format '{{.Names}}' | grep -qx 'sectors-db'; then
      echo "[setup] starting docker container: sectors-db"
      docker start sectors-db >/dev/null || true
      sleep 2
    fi
  fi
fi

# 3) Init DB + Tables if missing (safe to run every time)
echo "[setup] init-only (create DB/tables if missing)"
"$PY" "$COLLECT" --init-only >/dev/null

# 4) Write systemd service (oneshot)
cat > "$SERVICE_FILE" <<EOT
[Unit]
Description=Sector Stats Collector (collect_stats.py)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=jwan
Group=jwan
WorkingDirectory=$APP_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$PY $COLLECT
StandardOutput=append:$LOG_FILE
StandardError=append:$LOG_FILE
EOT

# 5) Write systemd timer (daily 01:00 local time)
cat > "$TIMER_FILE" <<'EOT'
[Unit]
Description=Run Sector Stats Collector daily at 01:00

[Timer]
OnCalendar=*-*-* 01:00:00
Persistent=true
RandomizedDelaySec=5m

[Install]
WantedBy=timers.target
EOT

# 6) Enable timer
systemctl daemon-reload
systemctl enable --now sector-collector.timer >/dev/null

echo "[setup] OK: timer installed & enabled"
echo "[setup] next runs:"
systemctl list-timers --all | grep -E 'sector-collector|NEXT' || true
