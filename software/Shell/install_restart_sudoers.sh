#!/usr/bin/env bash
set -euo pipefail

RUN_USER="$(id -un)"
SYSTEMCTL_PATH="$(command -v systemctl)"
SUDOERS_PATH="/etc/sudoers.d/cat-door-services"
TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

cat >"$TMP_FILE" <<EOF
${RUN_USER} ALL=(root) NOPASSWD: ${SYSTEMCTL_PATH} restart cat-door-camera.service, ${SYSTEMCTL_PATH} --no-block restart cat-door-monitor.service
EOF

sudo visudo -cf "$TMP_FILE"
sudo cp "$TMP_FILE" "$SUDOERS_PATH"
sudo chmod 440 "$SUDOERS_PATH"

echo "Installed narrow sudoers rule for cat door service restarts."
