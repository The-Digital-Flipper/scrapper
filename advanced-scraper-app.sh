#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/007-JB/advanced-scraper"
LOG_DIR="/home/007-JB/.advanced-scraper"
PID_FILE="$LOG_DIR/dashboard.pid"
DESKTOP_DIR="$APP_DIR/desktop"
URL="http://127.0.0.1:${ADVANCED_SCRAPER_PORT:-8801}"

mkdir -p "$LOG_DIR"

is_running() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
  else
    return 1
  fi
}

if [[ -x "$DESKTOP_DIR/node_modules/.bin/electron" ]]; then
  cd "$DESKTOP_DIR"
  exec ./node_modules/.bin/electron .
fi

if command -v electron >/dev/null 2>&1; then
  cd "$DESKTOP_DIR"
  exec electron .
fi

if ! is_running; then
  cd "$APP_DIR"
  nohup python3 -m advanced_scraper.product > "$LOG_DIR/dashboard.log" 2>&1 &
  echo "$!" > "$PID_FILE"
  sleep 1
fi

xdg-open "$URL" >/dev/null 2>&1 || true
