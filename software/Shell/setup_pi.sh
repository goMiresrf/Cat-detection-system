#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

if [ ! -d "$PROJECT_DIR/.venv" ]; then
  python3 -m venv --system-site-packages "$PROJECT_DIR/.venv"
elif ! grep -q "include-system-site-packages = true" "$PROJECT_DIR/.venv/pyvenv.cfg"; then
  echo "Warning: existing .venv cannot see Raspberry Pi OS camera packages."
  echo "To use the live stream, recreate it with:"
  echo "  rm -rf .venv"
  echo "  ./Shell/setup_pi.sh"
fi

source "$PROJECT_DIR/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$SCRIPT_DIR/requirements.txt"

if ! python -c "import picamera2" >/dev/null 2>&1; then
  echo "Warning: Picamera2 is not available in this Python environment."
  echo "On Raspberry Pi OS, install it with:"
  echo "  sudo apt install -y python3-picamera2"
fi

if [ ! -f "$PROJECT_DIR/cat_door/.env" ]; then
  cp "$PROJECT_DIR/cat_door/.env.example" "$PROJECT_DIR/cat_door/.env"
  echo "Created cat_door/.env from cat_door/.env.example"
fi

cat <<'EOF'
Setup complete.

Next steps:
1. Edit cat_door/.env with your Telegram token, chat ID, and hardware settings.
2. Run ./Shell/run_cat_door.sh status
3. Run ./Shell/run_cat_door.sh text-test
4. Run ./Shell/run_cat_door.sh approval-test
5. Run ./Shell/start_camera_stream.sh
EOF
