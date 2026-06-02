#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$(pwd)}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
SERVICE_NAME="${SERVICE_NAME:-outdoor-monitor}"
CAMERA_INDEX="${CAMERA_INDEX:-5}"
DEVICE_ID="${DEVICE_ID:-VF2-01}"
UPLOAD_URL="${UPLOAD_URL:-}"
SCKEY="${SCKEY:-}"
WORK_SEC="${WORK_SEC:-20}"
RECORD_SEC="${RECORD_SEC:-0}"
SAVE_DIR="${SAVE_DIR:-$APP_DIR/data}"
DETECT_MODE="${DETECT_MODE:-1}"
RESTART_SEC="${RESTART_SEC:-10}"

if [ -z "$UPLOAD_URL" ]; then
    echo "UPLOAD_URL is required. Example:"
    echo "UPLOAD_URL=http://192.168.137.1:5000/upload SCKEY=SCTxxx ./scripts/vf2_install_service.sh"
    exit 1
fi

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

mkdir -p "$SAVE_DIR/logs"

SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
TMP_SERVICE_FILE="/tmp/$SERVICE_NAME.service.$$"
ENV_FILE="/etc/$SERVICE_NAME.env"

PUSH_ARGS="--no-push"
ENV_LINE=""
if [ -n "$SCKEY" ]; then
    PUSH_ARGS=""
    ENV_LINE="EnvironmentFile=-$ENV_FILE"
    TMP_ENV_FILE="/tmp/$SERVICE_NAME.env.$$"
    cat <<EOF > "$TMP_ENV_FILE"
SCKEY=$SCKEY
EOF
    sudo install -m 0600 "$TMP_ENV_FILE" "$ENV_FILE"
    rm -f "$TMP_ENV_FILE"
else
    sudo rm -f "$ENV_FILE"
fi

EXEC_START="$VENV_DIR/bin/python $APP_DIR/monitor_uploader.py --camera-index $CAMERA_INDEX --device-id $DEVICE_ID --upload-url $UPLOAD_URL --work-sec $WORK_SEC --record-sec $RECORD_SEC --save-dir $SAVE_DIR --detect-mode $DETECT_MODE $PUSH_ARGS"

cat <<EOF > "$TMP_SERVICE_FILE"
[Unit]
Description=Outdoor Monitor on VisionFive 2
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
Environment=PYTHONUNBUFFERED=1
$ENV_LINE
ExecStart=$EXEC_START
Restart=always
RestartSec=$RESTART_SEC
StandardOutput=append:$SAVE_DIR/logs/monitor.log
StandardError=append:$SAVE_DIR/logs/monitor.log

[Install]
WantedBy=multi-user.target
EOF

sudo install -m 0644 "$TMP_SERVICE_FILE" "$SERVICE_FILE"
rm -f "$TMP_SERVICE_FILE"
sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE_NAME.service"

cat <<EOF
Service installed and started: $SERVICE_NAME.service

Useful commands:
  sudo systemctl status $SERVICE_NAME
  sudo systemctl restart $SERVICE_NAME
  sudo systemctl stop $SERVICE_NAME
  journalctl -u $SERVICE_NAME -f
  tail -f "$SAVE_DIR/logs/monitor.log"
EOF
