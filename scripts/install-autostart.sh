#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="$(command -v python3)"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT_FILE="$UNIT_DIR/sma-tqqq.service"

mkdir -p "$UNIT_DIR"
sed -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" -e "s|__PYTHON__|$PYTHON_BIN|g" \
  "$PROJECT_DIR/systemd/sma-tqqq.service.template" > "$UNIT_FILE"

systemctl --user daemon-reload
systemctl --user enable --now sma-tqqq.service

PORT="$(grep -s '^SMA_TQQQ_PORT=' "$PROJECT_DIR/.env" | cut -d= -f2 || true)"
PORT="${PORT:-8742}"
echo
echo "sma-tqqq is running and will start automatically at every login."
echo "Open http://127.0.0.1:$PORT"
echo "To start it at boot even before login, additionally run: loginctl enable-linger $USER"
