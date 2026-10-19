#!/usr/bin/env bash
set -euo pipefail

systemctl --user disable --now sma-tqqq.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/sma-tqqq.service"
systemctl --user daemon-reload
echo "sma-tqqq autostart removed."
