#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_NAME="${1:-cat-door-camera.service}"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"
RUN_USER="$(id -un)"
RUN_GROUP="$(id -gn)"

if [ ! -x "$PROJECT_DIR/.venv/bin/python" ]; then
  echo "Missing virtual environment. Run ./Shell/setup_pi.sh first."
  exit 1
fi

if [ ! -f "$PROJECT_DIR/cat_door/.env" ]; then
  echo "Missing cat_door/.env file. Copy cat_door/.env.example to cat_door/.env and configure it first."
  exit 1
fi

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

cat >"$TMP_FILE" <<EOF
[Unit]
Description=Cat door live camera stream
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
Group=${RUN_GROUP}
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/cat_door/.env
Environment=PYTHONUNBUFFERED=1
ExecStart=${PROJECT_DIR}/.venv/bin/python -m cat_door.live_stream
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo cp "$TMP_FILE" "$SERVICE_PATH"
sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE_NAME"
sudo systemctl status "$SERVICE_NAME" --no-pager
