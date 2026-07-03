#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

cat <<'EOF'
Setup complete.

Next steps:
1. Edit .env with your Telegram token, chat ID, and hardware settings.
2. Run ./run_cat_door.sh status
3. Run ./run_cat_door.sh text-test
4. Run ./run_cat_door.sh approval-test
EOF
