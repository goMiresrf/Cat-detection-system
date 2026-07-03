#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="${1:-cat-door-monitor.service}"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"
RUN_USER="$(id -un)"
RUN_GROUP="$(id -gn)"

if [ ! -x "$SCRIPT_DIR/.venv/bin/python" ]; then
  echo "Missing virtual environment. Run ./setup_pi.sh first."
  exit 1
fi

if [ ! -f "$SCRIPT_DIR/.env" ]; then
  echo "Missing .env file. Copy .env.example to .env and configure it first."
  exit 1
fi

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

cat >"$TMP_FILE" <<EOF
[Unit]
Description=Cat door monitor loop
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
Group=${RUN_GROUP}
WorkingDirectory=${SCRIPT_DIR}
EnvironmentFile=${SCRIPT_DIR}/.env
Environment=PYTHONUNBUFFERED=1
ExecStart=${SCRIPT_DIR}/.venv/bin/python -m cat_door.main monitor-loop
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo cp "$TMP_FILE" "$SERVICE_PATH"
sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE_NAME"
sudo systemctl status "$SERVICE_NAME" --no-pager
