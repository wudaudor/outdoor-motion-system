#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$(pwd)}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
SERVICE_NAME="${SERVICE_NAME:-outdoor-monitor-web}"
WEB_PORT="${WEB_PORT:-8000}"
RESTART_SEC="${RESTART_SEC:-5}"

if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "Python venv not found at $VENV_DIR/bin/python"
    echo "Run scripts/vf2_install_deps.sh first, or set VENV_DIR to the right path."
    exit 1
fi

sudo() {
    if [ -n "${SUDO_PASSWORD:-}" ]; then
        printf '%s\n' "$SUDO_PASSWORD" | command sudo -S -p '' "$@"
    else
        command sudo "$@"
    fi
}

mkdir -p "$APP_DIR/uploads"

SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
TMP_SERVICE_FILE="/tmp/$SERVICE_NAME.service.$$"

cat <<EOF > "$TMP_SERVICE_FILE"
[Unit]
Description=Outdoor Monitor Local Web UI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
Environment=PYTHONUNBUFFERED=1
Environment=MONITOR_WEB_PORT=$WEB_PORT
ExecStart=$VENV_DIR/bin/python $APP_DIR/server_receive.py
Restart=always
RestartSec=$RESTART_SEC
StandardOutput=append:$APP_DIR/data/logs/web.log
StandardError=append:$APP_DIR/data/logs/web.log

[Install]
WantedBy=multi-user.target
EOF

sudo install -m 0644 "$TMP_SERVICE_FILE" "$SERVICE_FILE"
rm -f "$TMP_SERVICE_FILE"

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "Installed $SERVICE_NAME on http://127.0.0.1:$WEB_PORT/"
