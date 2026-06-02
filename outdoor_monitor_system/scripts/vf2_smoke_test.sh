#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$(pwd)}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
CAMERA_INDEX="${CAMERA_INDEX:-4}"
UPLOAD_URL="${UPLOAD_URL:-}"

PYTHON_BIN="python3"
if [ -x "$VENV_DIR/bin/python" ]; then
    PYTHON_BIN="$VENV_DIR/bin/python"
fi

echo "==> Python module check"
"$PYTHON_BIN" - <<'PY'
modules = ["cv2", "numpy", "requests", "flask", "VisionFive.gpio"]
for name in modules:
    try:
        mod = __import__(name)
        version = getattr(mod, "__version__", "OK")
        print(f"{name}: {version}")
    except Exception as exc:
        print(f"{name}: FAILED: {exc}")
        raise
PY

echo
echo "==> Camera devices"
ls -l /dev/video* 2>/dev/null || true
if command -v v4l2-ctl >/dev/null 2>&1; then
    v4l2-ctl --list-devices || true
fi

echo
echo "==> Camera read test: /dev/video$CAMERA_INDEX"
"$PYTHON_BIN" - "$CAMERA_INDEX" <<'PY'
import sys
import cv2

index = int(sys.argv[1])
cap = cv2.VideoCapture(index)
try:
    if not cap.isOpened():
        raise SystemExit(f"Cannot open camera index {index}")
    ok, frame = cap.read()
    if not ok or frame is None:
        raise SystemExit(f"Cannot read one frame from camera index {index}")
    print(f"Read OK: shape={frame.shape}")
finally:
    cap.release()
PY

if [ -n "$UPLOAD_URL" ]; then
    echo
    echo "==> Upload server health"
    HEALTH_URL="${UPLOAD_URL%/upload}/health"
    curl -fsS "$HEALTH_URL"
    echo
fi

echo
echo "Smoke test OK"
