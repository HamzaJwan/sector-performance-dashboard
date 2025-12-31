#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/sector_analysis"
SYSTEMD_DIR="/etc/systemd/system"
COLLECTOR_SERVICE="sector-collector.service"
COLLECTOR_TIMER="sector-collector.timer"
BOOTSTRAP_SERVICE="sector-bootstrap.service"

log() { echo "[$(date -u +'%F %T')] $*"; }

need_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    log "ERROR: run as root. Use: sudo $0"
    exit 1
  fi
}

set_timezone_if_needed() {
  # إذا تبي تخليها UTC، علّق السطور التالية
  if command -v timedatectl >/dev/null 2>&1; then
    local tz
    tz="$(timedatectl show -p Timezone --value 2>/dev/null || true)"
    if [[ "$tz" != "Africa/Tripoli" ]]; then
      log "Timezone is '$tz' -> setting to Africa/Tripoli (so 01:00 is Libya local time)."
      timedatectl set-timezone Africa/Tripoli || true
    fi
  fi
}

wake_db_container_if_exists() {
  if command -v docker >/dev/null 2>&1; then
    if docker ps -a --format '{{.Names}}' | grep -qx 'sectors-db'; then
      log "Starting DB container: sectors-db"
      docker start sectors-db >/dev/null 2>&1 || true
    else
      log "DB container sectors-db not found (OK)."
    fi
  else
    log "docker not installed (OK if DB is external)."
  fi
}

ensure_db_tables() {
  if [[ -x "$APP_DIR/venv/bin/python" ]]; then
    log "Ensuring DB + tables via collect_stats.py --init-only"
    "$APP_DIR/venv/bin/python" "$APP_DIR/collect_stats.py" --init-only || true
  else
    log "WARNING: venv python not found at $APP_DIR/venv/bin/python"
  fi
}

install_systemd_units() {
  log "Installing/Updating systemd units"

  install -m 0644 "$APP_DIR/systemd/$COLLECTOR_SERVICE" "$SYSTEMD_DIR/$COLLECTOR_SERVICE"
  install -m 0644 "$APP_DIR/systemd/$COLLECTOR_TIMER"   "$SYSTEMD_DIR/$COLLECTOR_TIMER"
  install -m 0644 "$APP_DIR/systemd/$BOOTSTRAP_SERVICE"  "$SYSTEMD_DIR/$BOOTSTRAP_SERVICE"

  systemctl daemon-reload

  # فعل bootstrap (على كل Boot)
  systemctl enable "$BOOTSTRAP_SERVICE" >/dev/null 2>&1 || true

  # فعل التايمر
  systemctl enable --now "$COLLECTOR_TIMER" >/dev/null 2>&1 || true

  log "systemd OK. Next runs:"
  systemctl list-timers --all | grep -E 'sector-collector|NEXT|LEFT' || true
}

main() {
  need_root
  cd "$APP_DIR"

  set_timezone_if_needed
  wake_db_container_if_exists
  ensure_db_tables
  install_systemd_units

  log "BOOTSTRAP DONE."
  log "Manual test: systemctl start sector-collector.service"
  log "Log tail: tail -n 50 /opt/sector_analysis/collect_stats.log"
}

main "$@"
